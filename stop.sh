#!/bin/bash
# Tools 项目停止脚本
# =====================

echo -e "${YELLOW}停止 Tools 服务...${NC}"

# 停止 Django (daphne)
pkill -f "daphne" 2>/dev/null || true
pkill -f "manage.py runserver" 2>/dev/null || true
echo "- Django 已停止"

# 停止 Vue (npm/vite)
pkill -f "vite" 2>/dev/null || true
pkill -f "node.*vite" 2>/dev/null || true
echo "- Vue 前端已停止"

# 释放端口
fuser -k 6000/tcp 2>/dev/null || true
fuser -k 6500/tcp 2>/dev/null || true

echo -e "${GREEN}所有服务已停止${NC}"
