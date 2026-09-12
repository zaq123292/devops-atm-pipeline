# DevOps ATM 自助银行系统

Flask 教学项目，包含登录、余额、取款限额、存款、转账、交易记录、健康检查和 Prometheus 指标。

## 功能特性

- 卡号 + PIN 登录（演示账户：`10000001 / 1234`）
- 余额查询、取款（含日限额）、存款、行内转账、交易记录
- 金额以"分"为内部整数单位，避免浮点误差
- 参数化 SQL 查询，防止注入
- `/health` 健康检查端点（状态、运行时间、数据库连接）
- `/metrics` Prometheus 指标端点
- 支持 SQLite（开发）与 PostgreSQL（生产）双数据库

## 本地运行

```bash
pip install -r requirements.txt
python app.py
```

访问 `http://127.0.0.1:5000`，演示账户为 `10000001 / 1234`。

## 自动化测试

```bash
pytest tests/ --cov=. --cov-report=term-missing
flake8 app.py config.py --max-line-length=120 --ignore=E226,E302,E305,E306,E401,E501,E701,E702,E704
```

## Docker 部署（含监控）

```bash
cp .env.example .env
# 编辑 .env 设置 DB_PASSWORD
docker-compose up -d --build
```

服务列表：

| 服务 | 地址 |
|------|------|
| ATM 应用（Nginx） | http://localhost |
| 健康检查 | http://localhost/health |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin/admin) |

## CI/CD

- **Gitee Go**：`.workflow/ci-cd.yml` — 在 Gitee 仓库开通流水线后自动触发
- **GitHub Actions**：`.github/workflows/ci-cd.yml` — 推送到 master/develop 时触发

流水线阶段：`测试（pytest + flake8）→ Docker 构建 → 生产部署（手动）`

## 部署与回滚

```bash
# 部署指定版本
./scripts/deploy.sh v1.0.0

# 回滚到指定版本
./scripts/rollback.sh v1.0.0

# 完整回滚测试演示
./scripts/rollback_test.sh
```

## 文档

- [DevOps 报告](docs/DevOpsReport.md) — 架构图、CI/CD 流程、分支策略
- [截图获取指南](docs/ScreenshotGuide.md) — 5 类截图的详细获取步骤
- [告警规则](docs/AlertRules.md) — Prometheus 告警规则
- [分支策略](docs/BranchStrategy.md) — GitOps 分支管理
- [环境管理](docs/EnvManagement.md) — 开发/测试/生产环境
