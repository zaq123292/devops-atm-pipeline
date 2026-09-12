import logging, time, uuid
from datetime import date
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, flash, g, redirect, render_template, request, session, url_for, jsonify
from config import Config

try:
    from prometheus_flask_exporter import PrometheusMetrics
except ImportError:
    PrometheusMetrics = None


def _is_postgres(database_url):
    return isinstance(database_url, str) and database_url.startswith("postgresql")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(test_config or Config)
    if PrometheusMetrics:
        PrometheusMetrics(app)
    # 文件日志（按天轮转，保留 30 天）
    handler = TimedRotatingFileHandler("atm.log", when="midnight", backupCount=30, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    app.logger.addHandler(handler)
    # 控制台日志（Docker 容器可通过 docker-compose logs 查看）
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
    app.started_at = time.time()
    app.logger.info("ATM 应用启动，数据库类型: %s", "PostgreSQL" if _is_postgres(app.config.get("DATABASE", "")) else "SQLite")

    is_pg = _is_postgres(app.config.get("DATABASE", ""))

    def db():
        if "db" not in g:
            if is_pg:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                g.db = psycopg2.connect(app.config["DATABASE"], cursor_factory=RealDictCursor)
            else:
                import sqlite3
                g.db = sqlite3.connect(app.config["DATABASE"])
                g.db.row_factory = sqlite3.Row
        return g.db() if is_pg else g.db

    @app.teardown_appcontext
    def close_db(_error):
        connection = g.pop("db", None)
        if connection:
            connection.close()

    def init_db():
        connection = db()
        if is_pg:
            cur = connection.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS accounts(
                card TEXT PRIMARY KEY,
                pin TEXT NOT NULL,
                name TEXT NOT NULL,
                balance INTEGER NOT NULL
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS transactions(
                id SERIAL PRIMARY KEY,
                card TEXT NOT NULL,
                kind TEXT NOT NULL,
                amount INTEGER NOT NULL,
                detail TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            cur.execute("SELECT 1 FROM accounts WHERE card=%s", ("10000001",))
            if not cur.fetchone():
                cur.execute("INSERT INTO accounts VALUES (%s,%s,%s,%s)",
                            ("10000001", "1234", "演示用户", 500000))
            connection.commit()
            cur.close()
        else:
            connection.executescript("""CREATE TABLE IF NOT EXISTS accounts(
                card TEXT PRIMARY KEY, pin TEXT NOT NULL, name TEXT NOT NULL, balance INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card TEXT NOT NULL, kind TEXT NOT NULL, amount INTEGER NOT NULL,
                detail TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );""")
            if not connection.execute("SELECT 1 FROM accounts WHERE card='10000001'").fetchone():
                connection.execute("INSERT INTO accounts VALUES ('10000001','1234','演示用户',500000)")
            connection.commit()

    with app.app_context():
        init_db()

    def user():
        return session.get("card")

    def login_required():
        if not user():
            return redirect(url_for("login"))

    def amount_from_form():
        try:
            value = int(request.form.get("amount", "0"))
            if value <= 0 or value % 100 != 0:
                raise ValueError
            return value * 100
        except ValueError:
            return None

    def record(connection, card, kind, amount, detail=""):
        ph = "%s" if is_pg else "?"
        sql = f"INSERT INTO transactions(card,kind,amount,detail) VALUES ({ph},{ph},{ph},{ph})"
        if is_pg:
            connection.cursor().execute(sql, (card, kind, amount, detail))
        else:
            connection.execute(sql, (card, kind, amount, detail))

    @app.before_request
    def request_id():
        g.request_id = uuid.uuid4().hex[:8]

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            card = request.form.get("card", "")
            ph = "%s" if is_pg else "?"
            sql = f"SELECT card,name FROM accounts WHERE card={ph} AND pin={ph}"
            conn = db()
            if is_pg:
                cur = conn.cursor()
                cur.execute(sql, (card, request.form.get("pin", "")))
                row = cur.fetchone()
                cur.close()
            else:
                row = conn.execute(sql, (card, request.form.get("pin", ""))).fetchone()
            if row:
                session.clear()
                session["card"] = row["card"]
                session["name"] = row["name"]
                app.logger.info("用户登录成功: card=%s", card)
                return redirect(url_for("dashboard"))
            app.logger.warning("登录失败: card=%s", card)
            flash("卡号或 PIN 错误")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/dashboard")
    def dashboard():
        if (result := login_required()):
            return result
        ph = "%s" if is_pg else "?"
        conn = db()
        if is_pg:
            cur = conn.cursor()
            cur.execute(f"SELECT balance FROM accounts WHERE card={ph}", (user(),))
            balance = cur.fetchone()["balance"]
            cur.close()
        else:
            balance = conn.execute(f"SELECT balance FROM accounts WHERE card={ph}", (user(),)).fetchone()["balance"]
        return render_template("dashboard.html", balance=balance)

    @app.route("/withdraw", methods=["GET", "POST"])
    def withdraw():
        if (result := login_required()):
            return result
        if request.method == "POST":
            amount = amount_from_form()
            conn = db()
            ph = "%s" if is_pg else "?"
            date_expr = "DATE(created_at)" if is_pg else "date(created_at)"
            sql = f"SELECT COALESCE(SUM(amount),0) AS s FROM transactions WHERE card={ph} AND kind='withdraw' AND {date_expr}={ph}"
            if is_pg:
                cur = conn.cursor()
                cur.execute(sql, (user(), str(date.today())))
                spent = cur.fetchone()["s"]
                cur.execute(f"SELECT balance FROM accounts WHERE card={ph}", (user(),))
                account = cur.fetchone()
                cur.close()
            else:
                spent = conn.execute(sql, (user(), str(date.today()))).fetchone()["s"]
                account = conn.execute(f"SELECT balance FROM accounts WHERE card={ph}", (user(),)).fetchone()
            if not amount:
                flash("金额必须为正整数且为 100 的倍数")
            elif amount + spent > app.config["DAILY_WITHDRAWAL_LIMIT"]:
                flash("超过当日取款限额")
            elif amount > account["balance"]:
                flash("余额不足")
            else:
                if is_pg:
                    cur = conn.cursor()
                    cur.execute(f"UPDATE accounts SET balance=balance-{ph} WHERE card={ph}", (amount, user()))
                    cur.close()
                else:
                    conn.execute(f"UPDATE accounts SET balance=balance-{ph} WHERE card={ph}", (amount, user()))
                record(conn, user(), "withdraw", amount)
                conn.commit()
                flash("取款成功")
                return redirect(url_for("dashboard"))
        return render_template("withdraw.html")

    @app.route("/deposit", methods=["GET", "POST"])
    def deposit():
        if (result := login_required()):
            return result
        if request.method == "POST":
            amount = amount_from_form()
            if not amount:
                flash("金额必须为正整数且为 100 的倍数")
            else:
                conn = db()
                ph = "%s" if is_pg else "?"
                if is_pg:
                    cur = conn.cursor()
                    cur.execute(f"UPDATE accounts SET balance=balance+{ph} WHERE card={ph}", (amount, user()))
                    cur.close()
                else:
                    conn.execute(f"UPDATE accounts SET balance=balance+{ph} WHERE card={ph}", (amount, user()))
                record(conn, user(), "deposit", amount)
                conn.commit()
                flash("存款成功")
                return redirect(url_for("dashboard"))
        return render_template("deposit.html")

    @app.route("/transfer", methods=["GET", "POST"])
    def transfer():
        if (result := login_required()):
            return result
        if request.method == "POST":
            amount = amount_from_form()
            target = request.form.get("target", "").strip()
            conn = db()
            ph = "%s" if is_pg else "?"
            if is_pg:
                cur = conn.cursor()
                cur.execute(f"SELECT balance FROM accounts WHERE card={ph}", (user(),))
                src = cur.fetchone()
                cur.execute(f"SELECT card FROM accounts WHERE card={ph}", (target,))
                dst = cur.fetchone()
                cur.close()
            else:
                src = conn.execute(f"SELECT balance FROM accounts WHERE card={ph}", (user(),)).fetchone()
                dst = conn.execute(f"SELECT card FROM accounts WHERE card={ph}", (target,)).fetchone()
            if not amount:
                flash("金额必须为正整数且为 100 的倍数")
            elif not dst or target == user():
                flash("目标账户无效")
            elif amount > src["balance"]:
                flash("余额不足")
            else:
                if is_pg:
                    cur = conn.cursor()
                    cur.execute(f"UPDATE accounts SET balance=balance-{ph} WHERE card={ph}", (amount, user()))
                    cur.execute(f"UPDATE accounts SET balance=balance+{ph} WHERE card={ph}", (amount, target))
                    cur.close()
                else:
                    conn.execute(f"UPDATE accounts SET balance=balance-{ph} WHERE card={ph}", (amount, user()))
                    conn.execute(f"UPDATE accounts SET balance=balance+{ph} WHERE card={ph}", (amount, target))
                record(conn, user(), "transfer", amount, "to:" + target)
                record(conn, target, "received", amount, "from:" + user())
                conn.commit()
                flash("转账成功")
                return redirect(url_for("dashboard"))
        return render_template("transfer.html")

    @app.route("/history")
    def history():
        if (result := login_required()):
            return result
        ph = "%s" if is_pg else "?"
        conn = db()
        if is_pg:
            cur = conn.cursor()
            cur.execute(f"SELECT kind,amount,detail,created_at FROM transactions WHERE card={ph} ORDER BY id DESC", (user(),))
            rows = cur.fetchall()
            cur.close()
        else:
            rows = conn.execute(f"SELECT kind,amount,detail,created_at FROM transactions WHERE card={ph} ORDER BY id DESC", (user(),)).fetchall()
        return render_template("history.html", transactions=rows)

    @app.route("/health")
    def health():
        try:
            conn = db()
            if is_pg:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.close()
            else:
                conn.execute("SELECT 1").fetchone()
            state = "connected"
        except Exception as e:
            state = "unavailable"
            app.logger.error("健康检查失败: %s", e)
        status = "ok" if state == "connected" else "degraded"
        if state == "connected":
            app.logger.info("健康检查: status=%s, db=%s", status, state)
        return jsonify(
            status=status,
            uptime=int(time.time() - app.started_at),
            db_status=state,
        )

    return app


app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
