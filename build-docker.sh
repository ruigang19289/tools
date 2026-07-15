#!/bin/sh
# Tools 项目 Docker 镜像打包脚本

set -eu

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

IMAGE_NAME="tools-app"
IMAGE_TAG="${1:-latest}"
REGISTRY="${2:-}"
OUTPUT_TAR="${3:-}"
CONTAINER_NAME="sds-tools"
FULL_IMAGE_NAME="${REGISTRY}${IMAGE_NAME}:${IMAGE_TAG}"
ALPINE_TAR="/mnt/alpine.tar"
TOOLS_PLATFORM_TAR="/root/tools-app.tar"

printf "%b\n" "${YELLOW}================================${NC}"
printf "%b\n" "${YELLOW}开始打包 Docker 镜像${NC}"
printf "%b\n" "${YELLOW}================================${NC}"
printf -- "- 镜像名称: %s\n" "${FULL_IMAGE_NAME}"
if [ -n "${OUTPUT_TAR}" ]; then
    printf -- "- 导出文件: %s\n" "${OUTPUT_TAR}"
fi
printf "\n"

if [ ! -f "Dockerfile" ]; then
    printf "%b\n" "${RED}错误: Dockerfile 不存在${NC}"
    exit 1
fi

# 加载基础镜像
if [ -f "${TOOLS_PLATFORM_TAR}" ]; then
    printf "%b\n" "${GREEN}加载 tools-platform 基础镜像: ${TOOLS_PLATFORM_TAR}${NC}"
    docker load -i "${TOOLS_PLATFORM_TAR}"
elif docker image inspect tools-platform:latest > /dev/null 2>&1; then
    printf "%b\n" "${GREEN}使用已有的 tools-platform:latest 镜像${NC}"
else
    printf "%b\n" "${RED}错误: 基础镜像不存在${NC}"
    exit 1
fi
printf "\n"

printf "%b\n" "${GREEN}开始构建镜像...${NC}"
docker build -t "${FULL_IMAGE_NAME}" .

if [ -n "${OUTPUT_TAR}" ]; then
    printf "%b\n" "${GREEN}导出镜像...${NC}"
    docker save -o "${OUTPUT_TAR}" "${FULL_IMAGE_NAME}"
fi

printf "\n"
printf "%b\n" "${GREEN}================================${NC}"
printf "%b\n" "${GREEN}镜像打包完成！${NC}"
printf "%b\n" "${GREEN}================================${NC}"
printf "\n"
printf "镜像信息:\n"
docker image inspect "${FULL_IMAGE_NAME}" --format 'name={{index .RepoTags 0}} id={{.Id}} size={{.Size}}'
printf "\n"
printf "运行容器:\n"
printf "  docker run -d --name %s -p 6000:6000 -p 6500:6500 %s\n" "${CONTAINER_NAME}" "${FULL_IMAGE_NAME}"
printf "\n"
printf "查看日志:\n"
printf "  docker logs %s\n" "${CONTAINER_NAME}"
printf "\n"
printf "停止容器:\n"
printf "  docker rm -f %s\n" "${CONTAINER_NAME}"

if [ -n "${OUTPUT_TAR}" ]; then
    printf "\n导入镜像:\n"
    printf "  docker load -i %s\n" "${OUTPUT_TAR}"
fi
