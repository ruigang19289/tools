#!/bin/bash
# Tools 项目 Docker 镜像打包脚本
# =====================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
IMAGE_NAME="tools-platform"
IMAGE_TAG="${1:-latest}"
REGISTRY="${2:-}"

# 完整镜像名
FULL_IMAGE_NAME="${REGISTRY}${IMAGE_NAME}:${IMAGE_TAG}"

echo -e "${YELLOW}================================${NC}"
echo -e "${YELLOW}开始打包 Docker 镜像${NC}"
echo -e "${YELLOW}================================${NC}"
echo "- 镜像名称: ${FULL_IMAGE_NAME}"
echo ""

# 检查 Dockerfile 是否存在
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}错误: Dockerfile 不存在${NC}"
    exit 1
fi

# 停止运行中的容器（如果有）
echo -e "${GREEN}检查运行中的容器...${NC}"
CONTAINER_ID=$(docker ps -a --filter "name=${IMAGE_NAME}" -q)
if [ -n "$CONTAINER_ID" ]; then
    echo "停止已有容器..."
    docker stop $CONTAINER_ID 2>/dev/null || true
    docker rm $CONTAINER_ID 2>/dev/null || true
fi

# 构建镜像
echo -e "${GREEN}开始构建镜像 (这可能需要几分钟)...${NC}"
docker build -t ${FULL_IMAGE_NAME} .

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}镜像打包完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "镜像信息:"
docker images ${FULL_IMAGE_NAME}
echo ""
echo "运行容器:"
echo "  docker run -d -p 6000:6000 -p 6500:6500 --name ${IMAGE_NAME} ${FULL_IMAGE_NAME}"
echo ""
echo "查看日志:"
echo "  docker logs ${IMAGE_NAME}"
echo ""
echo "停止容器:"
echo "  docker stop ${IMAGE_NAME}"
