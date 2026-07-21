#!/bin/bash
# Tools 项目启动脚本
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

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境 (支持 Windows 和 Linux)
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate  # Windows
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate      # Linux/Mac
else
    echo -e "${RED}错误: 找不到虚拟环境激活脚本${NC}"
    exit 1
fi

# 安装依赖
echo -e "${YELLOW}检查并安装 Python 依赖...${NC}"
if [ -f "backend/requirements.txt" ]; then
    pip install -q -r backend/requirements.txt 2>/dev/null || true
else
    pip install -q django djangorestframework django-cors-headers channels daphne paramiko Pillow python-dotenv 2>/dev/null || true
fi

# 安装前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}安装前端依赖...${NC}"
    cd frontend
    npm install 2>/dev/null || true
    cd ..
fi

# 释放端口
fuser -k 6000/tcp 2>/dev/null || true
fuser -k 6500/tcp 2>/dev/null || true
sleep 1

# 启动 Django 后端 (端口 6000) - 使用 daphne
echo -e "${GREEN}启动 Django 后端 (端口 6000)...${NC}"
DAPHNE_CMD=""
if [ -x "./venv/Scripts/daphne" ]; then
    DAPHNE_CMD="./venv/Scripts/daphne"
elif [ -x "./venv/Scripts/daphne.exe" ]; then
    DAPHNE_CMD="./venv/Scripts/daphne.exe"
elif [ -x "./venv/bin/python" ] && ./venv/bin/python -m daphne --version >/dev/null 2>&1; then
    DAPHNE_CMD="./venv/bin/python -m daphne"
elif [ -x "./venv/bin/daphne" ] && ./venv/bin/daphne --version >/dev/null 2>&1; then
    DAPHNE_CMD="./venv/bin/daphne"
elif command -v daphne >/dev/null 2>&1; then
    DAPHNE_CMD="daphne"
else
    echo -e "${RED}错误: 找不到可用的 daphne 命令${NC}"
    exit 1
fi
nohup $DAPHNE_CMD -b 0.0.0.0 -p 6000 backend.asgi:application > logs/django.log 2>&1 &
DJANGO_PID=$!
echo "- Django PID: $DJANGO_PID"

# 启动 Vue 前端开发服务器 (端口 6500)
echo -e "${GREEN}启动 Vue 前端 (端口 6500)...${NC}"
cd frontend
nohup npm run dev > ../logs/vue.log 2>&1 &
VUE_PID=$!
cd ..
echo "- Vue PID: $VUE_PID"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Tools 项目启动成功！${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "Django 后端: http://localhost:6000"
echo -e "Vue 前端:   http://localhost:6500"
echo -e "API 健康检查: http://localhost:6000/api/health"
echo ""
echo -e "日志位置: logs/django.log, logs/vue.log"
echo ""
echo -e "停止服务: ./stop.sh"

# netstat -ano | grep :6000 | grep LISTENING
# taskkill //F //PID 22008
# ./venv/Scripts/daphne -b 0.0.0.0 -p 6000 backend.asgi:application > logs/django.log 2>&1 &
# cd frontend && npm run dev > ../logs/vue.log 2>&1 &
