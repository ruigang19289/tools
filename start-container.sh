#!/bin/bash

# 停止并删除已存在的容器
docker rm -f sds-tools 2>/dev/null || true

# 创建数据目录
mkdir -p /root/vdbench50407/output

# 启动容器
docker run -dit \
  --name=sds-tools \
  --restart=always \
  -v /root/vdbench50407/output/:/app/data/vdbench-result \
  -p 6500:6500 \
  vdbench-app:v1

echo "容器 sds-tools 已启动"
echo "访问地址: http://localhost:6500"
