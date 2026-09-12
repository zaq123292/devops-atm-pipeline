#!/usr/bin/env bash
# 手动回滚脚本：将服务回滚到指定版本
# 用法: ./scripts/rollback.sh <目标版本号>
# 示例: ./scripts/rollback.sh v1.0.0

set -e

if [ -z "$1" ]; then
    echo "用法: ./scripts/rollback.sh <版本号>"
    echo "示例: ./scripts/rollback.sh v1.0.0"
    echo ""
    echo "可用镜像版本:"
    docker images devops-atm --format "  {{.Tag}}" 2>/dev/null || echo "  (无)"
    exit 1
fi

ROLLBACK_VERSION="$1"
IMAGE_NAME="devops-atm"

echo "============================================"
echo "  手动回滚到版本: ${ROLLBACK_VERSION}"
echo "============================================"

# 检查镜像是否存在
if ! docker image inspect "${IMAGE_NAME}:${ROLLBACK_VERSION}" > /dev/null 2>&1; then
    echo "❌ 镜像 ${IMAGE_NAME}:${ROLLBACK_VERSION} 不存在"
    echo "可用版本:"
    docker images devops-atm --format "  {{.Tag}}"
    exit 1
fi

# 回滚
echo ""
echo "[1/3] 使用版本 ${ROLLBACK_VERSION} 重启服务..."
IMAGE_TAG="${ROLLBACK_VERSION}" docker-compose up -d --no-deps web nginx

# 健康检查
echo ""
echo "[2/3] 健康检查..."
sleep 8
if curl -sf http://localhost/health > /dev/null 2>&1; then
    echo "✅ 回滚成功！服务已恢复到 ${ROLLBACK_VERSION}"
    curl -s http://localhost/health
    echo ""
    echo "${ROLLBACK_VERSION}" > .current_version
else
    echo "❌ 回滚后健康检查失败，请人工介入"
    docker-compose logs web
    exit 1
fi

echo ""
echo "[3/3] 回滚完成"
echo "当前版本: $(cat .current_version)"
