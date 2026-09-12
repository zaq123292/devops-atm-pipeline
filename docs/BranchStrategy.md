# GitOps 分支策略
`feature/*` 经 PR 审核合并到 `develop`；通过 CI 后由 `develop` 合并到 `main`，`main` 触发受保护生产部署。版本采用 `v{major}.{minor}.{patch}`；紧急修复从 `main` 建立 `hotfix/*`，完成后合并回 main 和 develop。
