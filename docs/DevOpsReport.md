# DevOps 报告

## 一、端到端架构流程图（代码提交 → 生产部署 → 监控告警）

```mermaid
flowchart LR
    DEV["开发者提交代码<br/>git push"] --> TRIGGER{"触发 CI 流水线<br/>GitHub Actions"}

    subgraph CI["CI 持续集成"]
        direction TB
        TEST["单元测试 pytest<br/>覆盖率报告"]
        LINT["静态代码检查 flake8"]
        TEST --> LINT
    end

    TRIGGER --> CI
    CI -->|"测试通过"| BUILD["Docker 镜像构建<br/>tag = commit SHA"]
    CI -->|"测试失败"| FAIL["构建失败<br/>通知开发者"]

    BUILD --> APPROVE{"生产环境审批<br/>environment production"}
    APPROVE -->|"批准"| DEPLOY["CD 自动部署<br/>docker-compose up -d"]
    DEPLOY --> HEALTHCHECK{"健康检查<br/>curl /health"}

    HEALTHCHECK -->|"通过"| RUNNING["服务上线运行<br/>Nginx 80 to Flask 5000"]
    HEALTHCHECK -->|"失败"| ROLLBACK["自动回滚<br/>部署上一版本镜像"]

    subgraph PROD["生产环境"]
        direction TB
        NGINX["Nginx 反向代理 :80"]
        WEB["Flask + Gunicorn :5000<br/>登录 取款 存款 转账"]
        DB[("PostgreSQL<br/>账户与交易表")]
        NGINX --> WEB
        WEB --> DB
    end

    RUNNING --> PROD

    subgraph MONITOR["监控与告警"]
        direction TB
        METRICS[/"metrics<br/>Prometheus 指标"/]
        PROM["Prometheus 抓取<br/>scrape_interval 15s"]
        GRAFANA["Grafana 可视化面板"]
        ALERT["Alertmanager 告警<br/>5xx大于1% / P95大于2s / DB宕机"]
        WEB -.->|"暴露"| METRICS
        METRICS --> PROM
        PROM --> GRAFANA
        PROM -->|"触发规则"| ALERT
    end

    PROD -.->|"暴露 health 和 metrics"| MONITOR
    ALERT -.->|"告警通知"| DEV
```

## 二、分支策略与环境

```mermaid
gitGraph
    commit id: "init"
    branch develop
    checkout develop
    commit id: "feature-1"
    commit id: "feature-2"
    checkout main
    merge develop
    commit id: "release" tag: "v1.0.0"
    branch hotfix/fix-1
    checkout hotfix/fix-1
    commit id: "urgent-fix"
    checkout main
    merge hotfix/fix-1
    checkout develop
    merge hotfix/fix-1
```

## 三、说明

本仓库提供 CI/CD 定义；实际运行截图需在将仓库推送到 GitHub/Gitee、配置 Secrets 与部署主机后取得，不能由本地源代码替代。

- **CI 流水线**：Gitee Go（`.workflow/ci-cd.yml`）与 GitHub Actions（`.github/workflows/ci-cd.yml`）双平台配置
- **CD 部署**：Docker Compose 编排 PostgreSQL + Flask + Nginx + Prometheus + Grafana
- **监控**：`/health` 健康检查 + `/metrics` Prometheus 指标 + Grafana 面板 + 告警规则
- **回滚**：基于 Docker 镜像版本标签的快速回滚机制，部署失败自动回滚到上一稳定版本
