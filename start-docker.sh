#!/bin/bash
# Tools 项目启动脚本 (Docker版)
# =====================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 目录设置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 释放端口
fuser -k 6000/tcp 2>/dev/null || true
fuser -k 6500/tcp 2>/dev/null || true
sleep 1

# 启动 Django 后端 (端口 6000) - 使用 daphne
echo -e "${GREEN}启动 Django 后端 (端口 6000)...${NC}"
nohup daphne -b 0.0.0.0 -p 6000 backend.asgi:application > logs/django.log 2>&1 &
DJANGO_PID=$!
echo "- Django PID: $DJANGO_PID"

# 启动 Vue 前端 (端口 6500)
echo -e "${GREEN}启动 Vue 前端 (端口 6500)...${NC}"
cd frontend
nohup npm run dev -- --host 0.0.0.0 > ../logs/vue.log 2>&1 &
VUE_PID=$!
cd ..
echo "- Vue PID: $VUE_PID"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Tools 项目启动成功！${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "Django 后端: http://localhost:6000"
echo -e "Vue 前端:   http://localhost:6500"
echo ""
echo -e "日志位置: logs/django.log, logs/vue.log"

# 保持容器运行
tail -f /dev/null
