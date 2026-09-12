# 环境管理
开发：本地 Flask 与 SQLite；测试：pytest 使用内存 SQLite；生产：Docker、PostgreSQL、Nginx。`.env` 只保存本地 `DB_PASSWORD`，不得提交；CI/CD 通过 GitHub Secrets 注入部署主机、密钥及生产数据库密码。配置入口为 `config.py`。
