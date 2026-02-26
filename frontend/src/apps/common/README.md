# 公共组件和工具库

这个目录包含了前端应用中可复用的组件和工具函数。

## Composables (组合式函数)

### useSSHConnection.js

提供 SSH 连接的通用逻辑和状态管理。

**使用示例:**

```javascript
import { useSSHConnection, useHostList } from '@/apps/common/useSSHConnection'

// SSH 连接管理
const { connection, isConnecting, isFormValid, getConnectionConfig } = useSSHConnection()

// 主机列表管理
const { hosts, addHost, removeHost, getValidHosts } = useHostList([''])
```

**功能:**
- `useSSHConnection()`: SSH 连接配置和状态管理
  - `connection`: 连接配置对象 (host, port, username, password)
  - `isFormValid`: 表单验证状态
  - `getConnectionConfig()`: 获取连接配置
  - `resetConnection()`: 重置连接

- `useHostList()`: 主机列表管理
  - `hosts`: 主机列表数组
  - `addHost()`: 添加主机
  - `removeHost(index)`: 删除主机
  - `getValidHosts()`: 获取有效主机列表

### useNotification.js

提供统一的通知消息管理和终端输出管理。

**使用示例:**

```javascript
import { useNotification, useTerminal } from '@/apps/common/useNotification'

// 通知管理
const { notification, showSuccess, showError, showWarning } = useNotification()

showSuccess('操作成功')
showError('操作失败')

// 终端输出管理
const { lines, addLine, addSuccess, addError, clearLines } = useTerminal()

addSuccess('连接成功')
addError('连接失败')
```

## 组件

### SSHCredentials.vue

SSH 认证表单组件，包含主机、端口、用户名、密码输入。

**使用示例:**

```vue
<template>
  <SSHCredentials
    :connection="connection"
    title="SSH 认证"
    hostLabel="主机地址"
    @update:connection="handleConnectionUpdate"
  />
</template>

<script setup>
import SSHCredentials from '@/apps/common/SSHCredentials.vue'
import { useSSHConnection } from '@/apps/common/useSSHConnection'

const { connection } = useSSHConnection()
</script>
```

**Props:**
- `connection`: SSH 连接对象 (必需)
- `title`: 标题 (默认: "SSH 认证")
- `hostLabel`: 主机标签 (默认: "主机地址")
- `hostPlaceholder`: 主机占位符 (默认: "192.168.1.100")

### HostList.vue

主机列表管理组件，支持添加、删除主机，显示验证结果。

**使用示例:**

```vue
<template>
  <HostList
    :hosts="hosts"
    :validationResults="validationResults"
    title="测试主机"
    @update:hosts="hosts = $event"
  />
</template>

<script setup>
import HostList from '@/apps/common/HostList.vue'
import { useHostList } from '@/apps/common/useSSHConnection'

const { hosts, validationResults } = useHostList([''])
</script>
```

**Props:**
- `hosts`: 主机数组 (必需)
- `validationResults`: 验证结果数组
- `title`: 标题 (默认: "主机列表")
- `placeholder`: 输入占位符 (默认: "192.168.1.100")

### TerminalOutput.vue

终端输出显示组件，支持彩色输出、统计信息、自动滚动。

**使用示例:**

```vue
<template>
  <TerminalOutput
    :lines="lines"
    title="测试输出"
    :stats="{ success: 10, failed: 2 }"
    clearable
    showTimestamp
    @clear="clearLines"
  />
</template>

<script setup>
import TerminalOutput from '@/apps/common/TerminalOutput.vue'
import { useTerminal } from '@/apps/common/useNotification'

const { lines, clearLines } = useTerminal()
</script>
```

**Props:**
- `lines`: 输出行数组 (必需)
- `title`: 终端标题
- `stats`: 统计信息对象
- `clearable`: 是否显示清空按钮
- `showTimestamp`: 是否显示时间戳
- `emptyText`: 空状态文本
- `autoScroll`: 是否自动滚动

### NotificationToast.vue

通知提示组件，支持成功、错误、警告、信息四种类型。

**使用示例:**

```vue
<template>
  <NotificationToast :notification="notification" />
</template>

<script setup>
import NotificationToast from '@/apps/common/NotificationToast.vue'
import { useNotification } from '@/apps/common/useNotification'

const { notification } = useNotification()
</script>
```

**Props:**
- `notification`: 通知对象 (必需)
  - `show`: 是否显示
  - `message`: 消息内容
  - `type`: 类型 (success/error/warning/info)

## 使用建议

1. **SSH 连接**: 使用 `useSSHConnection` 和 `SSHCredentials` 组件
2. **主机列表**: 使用 `useHostList` 和 `HostList` 组件
3. **通知提示**: 使用 `useNotification` 和 `NotificationToast` 组件
4. **终端输出**: 使用 `useTerminal` 和 `TerminalOutput` 组件

这些组件和工具函数可以大大减少重复代码，提高开发效率和代码一致性。
