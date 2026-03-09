# 基于 Alpine 构建项目镜像
FROM alpine:latest

# 安装基础依赖
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nodejs \
    npm \
    bash \
    tzdata \
    openssh-client \
    curl \
    sshpass \
    nginx

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

# 创建工作目录
WORKDIR /app

# 复制项目文件
COPY . /app/

# 安装 Python 依赖 (使用国内镜像并重试)
RUN pip3 install --no-cache-dir --break-system-packages \
    -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    django \
    djangorestframework \
    django-cors-headers \
    channels \
    daphne \
    paramiko

# 安装前端依赖并构建
WORKDIR /app/frontend
RUN rm -rf node_modules package-lock.json && \
    npm install --registry=https://registry.npmmirror.com && \
    npm run build

# 返回工作目录
WORKDIR /app

# 暴露端口
EXPOSE 6000 6500

# 启动脚本
COPY start-docker.sh /app/start.sh
RUN chmod +x /app/start.sh

# 启动服务
CMD ["/app/start.sh"]
