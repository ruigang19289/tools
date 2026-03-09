# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tools - 一个 DevOps 工具平台，提供性能测试、系统监控、网络工具等功能。

## Commands

```bash
./start.sh    # 启动服务 (Django:6000, Vue:6500)
./stop.sh     # 停止所有服务

# Frontend
cd frontend
npm run dev       # 开发服务器 (端口 6500)
npm run build     # 生产构建

# Backend
./venv/bin/python manage.py migrate  # 数据库迁移
./venv/bin/daphne -b 0.0.0.0 -p 6000 backend.asgi:application  # 运行服务器
```

## Architecture

### Backend (Django + Channels)
- **Framework**: Django 4.2+, Django REST Framework, Channels (WebSocket)
- **Server**: Daphne (ASGI, 端口 6000)
- **Database**: SQLite

### Frontend (Vue 3)
- **Framework**: Vue 3.4+, Composition API, Vue Router, Pinia
- **Build Tool**: Vite 5.0
- **HTTP**: Axios (baseURL: `/api/v1`)

### 通信模式
- **HTTP API**: `/api/v1/` 下所有 REST 端点
- **WebSocket**:
  - `/api/ssh/ws` - SSH 实时终端
  - `/api/v1/perf/fio/ws` - FIO 性能测试实时输出
- **代理**: Vite 开发服务器代理 `/api` 到 Django:6000

### API 响应格式
```python
# 成功
{'status': 'success', 'data': {...}}

# 错误
{'status': 'error', 'error': 'message'}
```

## Key Patterns

1. **优先使用公共资源**:
   - **IMPORTANT**: 开发新功能前，先检查 `frontend/src/common.css` 和 `frontend/src/apps/common/` 是否有可复用的样式和组件
   - 如果存在公共样式（如 `.btn`, `.btn-primary` 等），直接使用，不要在组件的 scoped 样式中重新定义
   - 如果存在公共组件（如 `PageHeader.vue`, `SSHCredentials.vue` 等），优先复用
   - 避免在 scoped 样式中覆盖全局样式，保持样式一致性

2. **SSH Session 管理**: 全局 `ssh_sessions` 字典，使用 threading.Lock 线程安全

3. **WebSocket Consumer**: `AsyncWebsocketConsumer` 处理实时通信
   - SSH 终端: `SSHConsumer` 处理交互式终端
   - FIO 测试: `FIOTestConsumer` 处理实时输出和统计数据推送

4. **Mock 数据**: paramiko 不可用时返回模拟数据用于演示

5. **Vue 组件**: 使用 `<script setup>` Composition API 语法

6. **组件复用**: 使用 PageHeader 和 Notification 等公共组件

7. **路由配置**: 前端路由路径从 `@/views/` 改为 `@/apps/`

8. **公共工具**: 使用 `frontend/src/apps/common/` 下的 Composables 和组件
   - `useSSHConnection`: SSH 连接管理
   - `useNotification`: 通知和终端输出管理
   - `SSHCredentials.vue`: SSH 认证表单
   - `HostList.vue`: 主机列表管理
   - `TerminalOutput.vue`: 终端输出显示
   - `NotificationToast.vue`: 通知提示

9. **FIO 实时测试**:
   - 使用 WebSocket 推送实时输出和统计数据
   - 支持多主机并发测试，每个主机独立终端标签
   - 实时图表更新 (IOPS, 带宽, 延迟)
   - 多主机统计聚合: IOPS/带宽相加，延迟取平均值

10. **终端输出和结果区域的标准布局**:
   - 使用 `.terminal-header` 容器包含标题和控制按钮
   - 标题使用 `.section-title`，控制按钮使用 `.terminal-controls` 容器
   - `.terminal-controls` 使用 `display: flex; gap: 10px;` 排列按钮
   - 按钮使用 `.btn-compact` 样式（padding: 6px 12px, font-size: 12px）
   - 标准按钮组合：清空 + 下载（终端输出）或 下载 + 清空（测试结果）
   - 下载功能：终端输出下载为 txt，测试结果下载为 CSV
   - 示例代码：
     ```vue
     <div class="terminal-header">
       <h2 class="section-title">终端输出</h2>
       <div class="terminal-controls">
         <button class="btn btn-compact" @click="clearLog">清空</button>
         <button class="btn btn-compact" @click="downloadLog">下载</button>
       </div>
     </div>
     ```

11. **模块状态配置**:
   - 配置文件: `frontend/src/config/modules.js`
   - 控制 11 个模块的可用状态（true: 可用, false: 维护中）
   - 维护中的模块在首页显示为灰色，不可点击，标签显示"维护中"
   - 修改配置文件后刷新页面即可生效
   - 模块列表:
     - 性能测试: vdbench, monitor, fio, cosbench
     - 网络工具: ping, bond, iperf3, connection_test
     - 系统工具: ssh, system_init, database

## Directory Structure (前后端一致)

```
backend/apps/                 frontend/src/apps/
├── network/                  ├── network/
│   ├── PingScan/            │   ├── PingScan.vue
│   ├── bond/                │   ├── BondConfig.vue
│   ├── ConnectionTest/      │   ├── ConnectionTest.vue
│   └── NetworkReliabilityTest/ └── NetworkReliabilityTest_new.vue
│
├── performance/              ├── performance/
│   ├── vdbench/             │   ├── VDBench.vue
│   ├── monitor/             │   ├── Monitor.vue
│   ├── FIOTest/             │   ├── FIOTest.vue
│   └── CosBenchGenerator/   │   └── CosBenchGenerator.vue
│
└── system/                   └── system/
    ├── ssh/                      ├── SSHTerminal.vue
    ├── system_init/              ├── SystemInit.vue
    └── DatabaseTool/             └── DatabaseTool.vue

frontend/src/components/common/
├── PageHeader.vue           # 通用页面头部组件
└── Notification.vue         # 通用通知组件

frontend/src/config/
└── modules.js               # 模块状态配置
```

## Common Components

### PageHeader.vue
所有页面使用统一的白色头部组件，接受 icon, title, subtitle 三个 props。

### Layout Standards
- 左侧面板宽度统一为 320px (除 VDBench 和 Monitor 外)
- 使用 `grid-template-columns: 320px 1fr` 布局
- 公共样式定义在 `frontend/src/common.css`

## All Routes

| 路径 | 模块 | 对应组件 |
|------|------|---------|
| `/api/v1/perf/monitor/` | monitor | Monitor.vue |
| `/api/v1/perf/vdbench/` | vdbench | VDBench.vue |
| `/api/v1/perf/fio/` | FIOTest | FIOTest.vue |
| `/api/v1/perf/cosbench/` | CosBenchGenerator | CosBenchGenerator.vue |
| `/api/v1/network/ping/` | PingScan | PingScan.vue |
| `/api/v1/network/bond/` | bond | BondConfig.vue |
| `/api/v1/network/connection-test/` | ConnectionTest | ConnectionTest.vue |
| `/api/v1/network/iperf3/` | NetworkReliabilityTest | NetworkReliabilityTest_new.vue |
| `/api/v1/system/ssh/` | ssh | SSHTerminal.vue |
| `/api/v1/system/system-init/` | system_init | SystemInit.vue |
| `/api/v1/system/database/` | DatabaseTool | DatabaseTool.vue |

## Project Modules

项目共有 **11 个功能模块**:

**性能测试工具 (4个)**:
- VDBench 可视化
- 系统监控
- FIO 测试
- CosBench 配置文件生成

**网络工具 (4个)**:
- 网段扫描 (PingScan)
- 带宽测试 (iperf3)
- 持续网络测试
- 网络聚合配置 (Bond)

**系统工具 (3个)**:
- 终端连接 (SSH)
- 系统初始化
- 数据库连接工具 (PostgreSQL/MySQL)

## Recent Updates

### 2026-02-16: 网络带宽测试 UI 优化与统一按钮样式

**功能实现**:
1. **网络带宽测试页面 UI 优化**
   - 匹配 FIO 页面样式：紫色渐变背景、字体大小、左侧面板 320px
   - 主机配置模块：3行 textarea，端口+用户名一行，密码单独一行
   - 测试配置布局：测试网段+测试模式一行，端口+并发数+测试时长三列布局
   - CPU 绑定和起始核心单独行显示
   - 优化间距：终端输出和测试结果间距 15px，紫线和黑框间距 15px
   - 终端输出高度调整为 395px

2. **测试控制功能**
   - 添加"停止测试"按钮（测试进行中显示）
   - 测试网段必填验证（为空时禁用开始测试按钮）
   - 终端输出和测试结果保留功能（不自动清空）

3. **清空和下载功能**
   - 终端输出：清空 + 下载按钮（下载为 txt 文件）
   - 测试结果：下载 + 清空按钮（下载为 CSV 格式）
   - FIO 页面：添加终端输出下载按钮
   - 文件名包含时间戳和主机信息

4. **统一按钮样式**
   - 更新 `common.css` 中 `.btn-compact` 样式：padding: 6px 12px, font-size: 12px
   - 移除固定宽度，使用 `width: auto`
   - 统一 FIO、VDBench、NetworkReliabilityTest 页面按钮样式
   - 添加 `.terminal-controls` 容器样式：`display: flex; gap: 10px`

5. **测试结果表格优化**
   - 移除测试类型列（One2One/RoundRobin）
   - 优化表格间距和对齐
   - 测试结果区域固定高度 400px，可滚动

**关键文件**:
- `frontend/src/common.css` - 更新全局 `.btn-compact` 样式
- `frontend/src/apps/network/NetworkReliabilityTest_new.vue` - 网络带宽测试页面
- `frontend/src/apps/performance/FIOTest.vue` - 添加下载按钮
- `frontend/src/apps/performance/VDBench.vue` - 统一按钮样式
- `CLAUDE.md` - 记录终端输出和结果区域的标准布局模式

**技术要点**:
- 使用 `.terminal-header` + `.terminal-controls` 标准布局
- 下载功能使用 Blob API 和 URL.createObjectURL
- CSV 格式导出测试结果数据
- 使用 `!important` 确保本地样式覆盖生效

### 2026-02-15: FIO 性能测试 WebSocket 实时输出

**功能实现**:
1. **WebSocket 实时通信**
   - 添加 FIO WebSocket 路由: `/api/v1/perf/fio/ws`
   - 创建 `FIOTestConsumer` 处理实时消息推送
   - Vite 代理配置支持 FIO WebSocket

2. **多主机独立终端**
   - 每个主机独立的终端标签页
   - 实时输出按主机分组显示
   - 支持多主机并发测试

3. **实时图表更新**
   - IOPS、带宽、延迟三个实时图表
   - 使用 Chart.js 显示性能曲线
   - 移除 60 点限制，显示完整测试时长
   - 使用 `toRaw()` 避免 Vue 响应式循环引用

4. **FIO 输出解析**
   - IOPS 解析支持 k/m 后缀 (如 19.6k = 19600)
   - 带宽解析支持 MiB/s 格式
   - 延迟解析修复正则表达式 (`.*?` 替代 `[^,]+`)
   - 只在解析到延迟行时发送完整统计数据

5. **多主机统计聚合**
   - IOPS: 所有主机相加
   - 带宽: 所有主机相加
   - 延迟: 所有主机平均值
   - 200ms 聚合延迟等待所有主机数据

**关键文件**:
- `backend/apps/performance/FIOTest/views.py` - FIO 测试逻辑和 WebSocket Consumer
- `backend/apps/performance/FIOTest/routing.py` - WebSocket 路由配置
- `backend/asgi.py` - 合并 SSH 和 FIO WebSocket 路由
- `frontend/vite.config.js` - FIO WebSocket 代理配置
- `frontend/src/apps/performance/FIOTest.vue` - 前端实时显示和图表

**技术要点**:
- FIO 命令添加 `--status-interval=1` 参数实现每秒输出
- 使用 `threading` 在后台线程执行 FIO 测试
- WebSocket 消息类型: `output`, `stats`, `completed`, `error`
- Chart.js 使用 `update('none')` 模式禁用动画提高性能

### 2026-02-16: 网络带宽测试完全重写

**功能实现**:
1. **基于 iperf3-bench 架构**
   - 完全重写后端和前端实现
   - 使用 SSH 远程执行 iperf3 命令
   - 支持多端口并发测试和 CPU 核心绑定

2. **三种测试模式**
   - **one2one**: 第一台主机作为服务端，其他主机依次向其发送数据（测试单点接收能力）
   - **roundrobin**: 每台主机互相发送数据，形成环形拓扑（测试全网互通性能）
   - **alltest**: 依次执行 one2one 和 roundrobin 两种测试（全面评估）

3. **实时日志和结果**
   - 后台线程执行测试，前端轮询获取状态
   - 实时显示测试日志和进度
   - 结果表格显示每对主机的带宽数据

4. **主机验证**
   - 测试前验证 SSH 连接
   - 显示每台主机的连接状态

**关键文件**:
- `backend/apps/network/NetworkReliabilityTest/views_new.py` - 新的带宽测试后端
- `backend/apps/network/NetworkReliabilityTest/urls.py` - 更新为使用 views_new
- `frontend/src/apps/network/NetworkReliabilityTest_new.vue` - 新的前端组件
- `frontend/src/router/index.js` - 路由更新为使用新组件

**API 端点**:
- `POST /api/v1/network/iperf3/start` - 启动测试
- `GET /api/v1/network/iperf3/results/<task_id>` - 获取测试状态和结果
- `DELETE /api/v1/network/iperf3/cancel/<task_id>` - 取消测试
- `POST /api/v1/network/iperf3/validate` - 验证主机连接

**技术要点**:
- 使用 paramiko 执行远程 SSH 命令
- iperf3 服务端: `iperf3 -s -p <port> -D` 后台运行
- iperf3 客户端: `iperf3 -c <server> -p <port> -t <duration> -P <parallel>`
- CPU 绑定: `taskset -c <core> <command>`
- 带宽解析: 从 iperf3 输出提取 "sender" 行的 Gbits/sec 值
- 后台线程 + 轮询模式实现异步测试

### 2026-02-26: CosBench 配置生成器优化

**功能实现**:
1. **标签页顺序调整**
   - Workload.xml 和 Controller.conf 位置交换
   - 生成配置后默认展示 Workload.xml

2. **读写混合支持**
   - 新增 "Mixed (混合读写)" 操作类型
   - 支持自定义读比例（写比例自动计算: 100 - 读比例）
   - 混合模式下写对象前缀 = 读对象前缀 + 1

3. **代码优化**
   - 移除未使用的变量和 computed
   - 简化读写比例逻辑

4. **模块配置**
   - 持续网络测试 (connection_test) 设置为维护模式

**关键文件**:
- `frontend/src/apps/performance/CosBenchGenerator.vue` - CosBench 前端组件
- `backend/apps/performance/CosBenchGenerator/views.py` - CosBench 后端
- `frontend/src/config/modules.js` - 模块状态配置

**技术要点**:
- 混合读写 XML 生成两个 operation 节点，分别指定 ratio
- 读写比例: read_ratio + write_ratio = 100
- 写对象前缀: obj-{driver_id+1:04d}- 读对象前缀: obj-{driver_id:04d}-

### 2026-03-09: 彻底删除两个功能模块

**功能实现**:
1. **彻底删除持续网络测试模块**
   - 删除前端路由 `/network/connection-test`
   - 删除前端组件 `frontend/src/apps/network/ConnectionTest.vue`
   - 删除后端目录 `backend/apps/network/ConnectionTest/`
   - 删除后端 URL 配置

2. **彻底删除数据库连接工具模块**
   - 删除前端路由 `/system/database`
   - 删除前端组件 `frontend/src/apps/system/DatabaseTool.vue`
   - 删除后端目录 `backend/apps/system/DatabaseTool/`
   - 删除后端 URL 配置

3. **更新首页和配置**
   - 删除首页链接
   - 移除 `frontend/src/config/modules.js` 中的 `connection_test` 和 `database` 配置

**关键文件**:
- `frontend/src/router/index.js` - 移除两个路由
- `frontend/src/views/Home.vue` - 移除两个首页链接
- `frontend/src/config/modules.js` - 移除模块配置
- `backend/apps/network/urls.py` - 移除 connection-test 路由
- `backend/apps/system/urls.py` - 移除 database 路由

### 2026-03-09: 调整首页模块布局

**功能实现**:
1. **系统监控移到系统工具**
   - 将系统监控从"测试工具"移到"系统工具"
   - 系统工具顺序: 系统监控, 终端连接, 系统初始化

2. **网络工具顺序调整**
   - 将"网络聚合配置"和"带宽测试"位置对调
   - 网络工具顺序: 网段扫描, 网络聚合配置, 带宽测试

**关键文件**:
- `frontend/src/views/Home.vue` - 调整模块位置

### 2026-03-09: 系统初始化主机名自动生成优化

**功能实现**:
1. **主机名自动生成逻辑**
   - 基于主机前缀 + IP排序序号自动生成主机名
   - IP按数值大小排序（如 192.168.1.50 < 192.168.1.100 < 192.168.1.200）
   - 序号从1开始，保留2位（如 node01, node02, node03）

2. **前端界面修改**
   - "主机名列表"改为"主机名前缀"输入框
   - 默认前缀: node
   - 移除手动输入主机名列表的功能

3. **后端逻辑修改**
   - 新增 `ip_to_int(ip)`: IP转整数用于排序
   - 新增 `sort_hosts_by_ip(hosts)`: 按IP数值排序
   - 修改 `generate_hostname_from_ip(ip, index, prefix)`: 支持自定义前缀
   - 修改 `full_init` 和 `modify_hostnames`: 自动排序并生成主机名

**关键文件**:
- `frontend/src/apps/system/SystemInit.vue` - 前端界面修改
- `backend/apps/system/system_init/views.py` - 后端逻辑修改

**使用示例**:
- 输入IP: 192.168.1.200, 192.168.1.50, 192.168.1.100
- 前缀: node
- 输出: node01 (192.168.1.50), node02 (192.168.1.100), node03 (192.168.1.200)

### 2026-03-09: 所有功能模块默认用户名设置为root

**功能实现**:
1. **所有SSH连接相关模块**
   - 系统初始化: 默认用户名 root
   - 系统监控: 默认用户名 root
   - 网络聚合配置: 默认用户名 root
   - FIO测试: 默认用户名 root
   - 带宽测试: 默认用户名 root
   - SSH终端: 默认用户名 root

**关键文件**:
- `frontend/src/apps/system/SystemInit.vue`
- `frontend/src/apps/performance/Monitor.vue`
- `frontend/src/apps/network/BondConfig.vue`
- `frontend/src/apps/performance/FIOTest.vue`
- `frontend/src/apps/network/NetworkReliabilityTest_new.vue`
- `frontend/src/apps/network/NetworkReliabilityTest.vue`
- `frontend/src/apps/system/SSHTerminal.vue`
- `frontend/src/apps/system/SSHTerminal_fio_copy.vue`
- `frontend/src/apps/system/SSHTerminal_new.vue`
- `frontend/src/apps/common/useSSHConnection.js`

