# 截图获取指南

本指南对应作业要求的 5 类截图，每类均给出具体操作步骤和截图要点。

---

## 1. 架构图：从代码提交到生产部署的完整流程图

**位置**：`docs/DevOpsReport.md` 第一节

**获取方式**：
- 在 Gitee 仓库页面打开 `docs/DevOpsReport.md`，Mermaid 图自动渲染
- 或在本地用 VS Code + Markdown Preview Mermaid Support 扩展预览（`Ctrl+Shift+V`）

**截图要点**：
- 完整展示：代码提交 → CI 测试 → 构建镜像 → CD 部署 → 监控告警 的全链路
- 包含失败回滚路径（健康检查失败 → 自动回滚）
- 包含生产环境组件（Nginx、Flask、PostgreSQL）和监控组件（Prometheus、Grafana、Alertmanager）

---

## 2. CI 流水线截图：GitHub Actions 运行成功

**前置条件**：将仓库推送到 GitHub（Gitee 也有 Gitee Go 流水线配置 `.workflow/ci-cd.yml`）

### 推送到 GitHub
```bash
# 在 GitHub 创建空仓库后，添加远程
git remote add github https://github.com/<你的用户名>/devops-atm-pipeline.git
git push github master
```

### 触发并查看
1. 进入 GitHub 仓库 → 点击 **Actions** 标签
2. 推送代码到 `master` 分支会自动触发 `CI/CD Pipeline` 工作流
3. 工作流包含三个 Job：`test` → `build` → `deploy`
4. 点击进入运行记录，展开各步骤查看日志

### 需截图的内容
- **Actions 列表页**：显示工作流状态为绿色 ✓（成功）
- **test Job 日志**：显示 `5 passed`、覆盖率报告、flake8 通过
- **build Job 日志**：显示 Docker 镜像构建成功
- **deploy Job 日志**：显示 docker compose 部署、健康检查通过、`/health` 和 `/metrics` 验证

---

## 3. CD 部署截图：部署日志展示自动部署过程

**前置条件**：安装 Docker Desktop

### 本地部署
```bash
cp .env.example .env
# 编辑 .env 设置 DB_PASSWORD
docker compose up -d --build
```

### 查看部署日志
```bash
# 查看所有服务日志
docker compose logs

# 只看 web 服务日志
docker compose logs web

# 查看容器运行状态
docker compose ps
```

### 需截图的内容
- `docker compose up -d --build` 的终端输出（显示各服务构建和启动）
- `docker compose ps` 输出（所有服务状态为 running）
- `docker compose logs web` 输出（显示应用启动日志、数据库连接、健康检查日志）

---

## 4. 监控截图：健康检查、日志输出、指标数据

### 健康检查
```bash
curl http://localhost/health
```
返回示例：
```json
{"status":"ok","uptime":120,"db_status":"connected"}
```

### 日志输出
```bash
# 实时查看日志
docker compose logs -f web
```
日志包含：应用启动、用户登录、健康检查、数据库操作等

### 指标数据
```bash
# 查看 Prometheus 原始指标
curl http://localhost:5000/metrics
```

### Prometheus UI
- 访问 `http://localhost:9090`
- 查询 `up{job="atm"}` → Execute → 截图
- 访问 `http://localhost:9090/targets` 查看抓取状态 → 截图
- 访问 `http://localhost:9090/alerts` 查看告警规则 → 截图

### Grafana 面板
- 访问 `http://localhost:3000`（账号 admin / admin）
- Dashboards → ATM → 「ATM 系统监控面板」→ 截图
- 面板包含：QPS、P95 延迟、服务存活、内存使用

### 需截图的内容
- `/health` 端点返回的 JSON
- `docker-compose logs web` 的日志输出
- `/metrics` 端点的指标数据
- Prometheus UI 的查询结果或 targets 页面
- Grafana 的 ATM 监控面板

---

## 5. 回滚测试：模拟部署失败并演示自动回滚

### 前置条件
- Docker Desktop 已启动
- 已运行 `docker compose up -d db` 启动数据库（回滚测试只重启 web 服务）

### 执行回滚测试
```bash
# 一键运行完整回滚测试
./scripts/rollback_test.sh
```

### 测试流程说明
1. **部署 v1.0.0 稳定版本**（使用正常的 `Dockerfile`）
   - 构建镜像 → 启动容器 → 健康检查通过
2. **部署 v2.0.0 有缺陷版本**（使用 `Dockerfile.broken`，故意引用不存在的模块）
   - 构建镜像 → 启动容器 → 健康检查失败
   - **自动触发回滚**：检测到健康检查失败，自动切换回 v1.0.0
3. **验证回滚结果**
   - 确认当前版本为 v1.0.0
   - 确认健康检查通过

### 手动分步演示（如需单独截图）
```bash
# 步骤 1：部署稳定版本
DOCKERFILE=Dockerfile ./scripts/deploy.sh v1.0.0

# 步骤 2：部署有缺陷版本（会触发自动回滚）
DOCKERFILE=Dockerfile.broken ./scripts/deploy.sh v2.0.0

# 步骤 3：验证回滚成功
curl http://localhost/health
cat .current_version   # 应显示 v1.0.0
```

### 需截图的内容
- 部署 v1.0.0 成功的终端输出（健康检查通过）
- 部署 v2.0.0 失败的终端输出（健康检查失败 + 自动回滚提示）
- 回滚后服务恢复正常的终端输出（当前版本 v1.0.0）
- 最终 `curl http://localhost/health` 返回正常状态

---

## 端口速查

| 服务 | 地址 |
|------|------|
| ATM 应用（Nginx） | http://localhost |
| ATM 应用（直连） | http://localhost:5000 |
| 健康检查 | http://localhost/health |
| Prometheus 指标 | http://localhost:5000/metrics |
| Prometheus UI | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin/admin) |
