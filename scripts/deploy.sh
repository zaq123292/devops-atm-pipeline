#!/usr/bin/env bash
# CD 部署脚本：构建带版本标签的 Docker 镜像，部署并做健康检查
# 若健康检查失败，自动回滚到上一稳定版本
# 用法: ./scripts/deploy.sh [版本号]
# 示例: ./scripts/deploy.sh v1.0.0

set -e

VERSION=${1:-v$(date +%Y%m%d%H%M%S)}
IMAGE_NAME="devops-atm"
IMAGE_TAG="${IMAGE_NAME}:${VERSION}"
DOCKERFILE=${DOCKERFILE:-Dockerfile}

echo "============================================"
echo "  CD 自动部署"
echo "  版本: ${VERSION}"
echo "  镜像: ${IMAGE_TAG}"
echo "  Dockerfile: ${DOCKERFILE}"
echo "============================================"

# 记录上一版本（用于回滚）
PREV_VERSION=""
if [ -f ".current_version" ]; then
    PREV_VERSION=$(cat .current_version)
fi

# 1. 构建镜像
echo ""
echo "[1/5] 构建 Docker 镜像: ${IMAGE_TAG}"
docker build -f "${DOCKERFILE}" -t "${IMAGE_TAG}" -t "${IMAGE_NAME}:latest" .
echo "✅ 镜像构建完成"

# 2. 部署新版本
echo ""
echo "[2/5] 部署新版本 ${VERSION}..."
IMAGE_TAG="${VERSION}" docker-compose up -d --no-deps web nginx
echo "✅ 新版本容器已启动"

# 3. 等待服务就绪
echo ""
echo "[3/5] 等待服务就绪（最多 60 秒）..."
DEPLOY_SUCCESS=false
for i in $(seq 1 12); do
    if curl -sf http://localhost/health > /dev/null 2>&1; then
        DEPLOY_SUCCESS=true
        break
    fi
    echo "  尝试 $i/12: 服务尚未就绪，等待 5 秒..."
    sleep 5
done

# 4. 健康检查与自动回滚
echo ""
echo "[4/5] 健康检查结果"
if [ "${DEPLOY_SUCCESS}" = true ]; then
    echo "✅ 健康检查通过！"
    curl -s http://localhost/health
    echo ""
    echo "${VERSION}" > .current_version
    echo "🎉 部署成功！当前版本: ${VERSION}"
else
    echo "❌ 健康检查失败！新版本 ${VERSION} 无法启动"
    echo ""
    echo "============================================"
    echo "  🔄 自动回滚到上一稳定版本"
    echo "============================================"
    if [ -n "${PREV_VERSION}" ]; then
        echo "回滚到版本: ${PREV_VERSION}"
        IMAGE_TAG="${PREV_VERSION}" docker-compose up -d --no-deps web nginx
        # 验证回滚
        sleep 8
        if curl -sf http://localhost/health > /dev/null 2>&1; then
            echo "✅ 回滚成功！服务已恢复到 ${PREV_VERSION}"
            curl -s http://localhost/health
            echo ""
            echo "${PREV_VERSION}" > .current_version
        else
            echo "❌ 回滚后健康检查仍失败，请人工介入"
            exit 1
        fi
    else
        echo "❌ 没有可用的上一版本，无法自动回滚"
        exit 1
    fi
    echo "⚠️  部署 ${VERSION} 失败，已回滚到 ${PREV_VERSION}"
    exit 1
fi

# 5. 显示部署日志
echo ""
echo "[5/5] 部署日志（web 服务）"
echo "--------------------------------------------"
docker-compose logs --tail=20 web
echo "--------------------------------------------"
echo ""
echo "当前运行容器:"
docker-compose ps
