import logging
import time
from logging.handlers import TimedRotatingFileHandler

from flask import Flask, g, jsonify, render_template

from config import Config


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(test_config or Config)

    # 日志配置：按天轮转，保留 30 天
    handler = TimedRotatingFileHandler(
        "atm.log", when="midnight", backupCount=30, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    app.logger.addHandler(handler)
    app.started_at = time.time()

    @app.before_request
    def before_request():
        g.request_start = time.time()

    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/health")
    def health():
        try:
            from app import get_db

            conn = get_db()
            conn.execute("SELECT 1")
            db_status = "up"
        except Exception:
            db_status = "down"
        return jsonify(
            status="ok", uptime=int(time.time() - app.started_at), db_status=db_status
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
