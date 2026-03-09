<template>
  <div class="ssh-terminal-page">
    <PageHeader
      icon="💻"
      title="终端连接"
    />

    <!-- Main Content -->
    <div class="main-content">
      <!-- Left Panel: Configuration -->
      <div class="left-panel">
        <!-- Connection Type -->
        <div class="section">
          <h2 class="section-title">连接类型</h2>

          <div class="connection-type-grid">
            <label class="radio-card" :class="{ active: connectionType === 'ssh' }">
              <input type="radio" v-model="connectionType" value="ssh">
              <span class="radio-icon">🔐</span>
              <span class="radio-name">SSH终端</span>
            </label>
            <label class="radio-card" :class="{ active: connectionType === 'file' }">
              <input type="radio" v-model="connectionType" value="file">
              <span class="radio-icon">📁</span>
              <span class="radio-name">文件管理</span>
            </label>
          </div>
        </div>

        <!-- Host Configuration -->
        <div class="section">
          <h2 class="section-title">主机配置</h2>

          <div class="form-group">
            <label>远程主机:</label>
            <input type="text" v-model="config.host" placeholder="192.168.1.1">
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>用户名:</label>
              <input type="text" v-model="config.username" placeholder="root">
            </div>
            <div class="form-group">
              <label>端口:</label>
              <input type="number" v-model="config.port" placeholder="22">
            </div>
          </div>

          <div class="form-group">
            <label>密码:</label>
            <input type="password" v-model="config.password" placeholder="******">
          </div>

          <button class="btn btn-primary btn-full" @click="connect" :disabled="!canConnect">
            连接
          </button>
        </div>
      </div>

      <!-- Right Panel: Terminal Section -->
      <div class="right-panel">
        <div class="terminal-section">
          <div class="terminal-header">
            <div class="terminal-title-group">
              <span class="terminal-title">终端输出</span>
            </div>
          </div>

          <!-- Host Tabs -->
          <div v-if="connectedHosts.length > 0" class="host-tabs">
            <div
              v-for="(host, index) in connectedHosts"
              :key="index"
              class="host-tab"
              :class="{ active: activeHostTab === host }"
              @click="activeHostTab = host"
            >
              {{ host }}
              <span style="margin-left: 8px; opacity: 0.6;" @click.stop="closeHost(host)">×</span>
            </div>
          </div>

          <div class="terminal-window" ref="terminalWindow">
            <div v-if="getCurrentTerminalLines().length === 0" class="terminal-empty">
              输入连接信息后点击"连接"按钮
            </div>
            <div
              v-for="(line, index) in getCurrentTerminalLines()"
              :key="index"
              class="terminal-line"
              :class="line.type"
            >
              {{ line.text }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Notification -->
    <div class="notification" :class="notification.type" v-if="notification.show">
      {{ notification.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'

const API_BASE = `/api/v1/system/ssh`

// Configuration
const config = reactive({
  host: '',
  username: 'root',
  password: '',
  port: 22
})

// Connection type
const connectionType = ref('ssh')

// Terminal
const terminalWindow = ref(null)
const hostTerminals = ref({}) // 每个主机的独立终端输出
const activeHostTab = ref('') // 当前激活的主机标签
const connectedHosts = ref([])

// Notification
const notification = reactive({
  show: false,
  message: '',
  type: 'info'
})

// Computed
const canConnect = computed(() => {
  return config.host && config.username && config.password
})

// Get current terminal lines
const getCurrentTerminalLines = () => {
  if (!activeHostTab.value) return []
  return hostTerminals.value[activeHostTab.value] || []
}

// Add terminal output
const addTerminalOutput = (host, text, type = 'info') => {
  if (!hostTerminals.value[host]) {
    hostTerminals.value[host] = []
  }
  hostTerminals.value[host].push({ text, type })

  nextTick(() => {
    if (terminalWindow.value) {
      terminalWindow.value.scrollTop = terminalWindow.value.scrollHeight
    }
  })
}

// Notification
const showNotification = (message, type = 'info') => {
  notification.message = message
  notification.type = type
  notification.show = true
  setTimeout(() => {
    notification.show = false
  }, 3000)
}

// Connect
const connect = async () => {
  if (!canConnect.value) return

  const hostKey = `${connectionType.value[0]}${config.host}`

  if (connectedHosts.value.includes(hostKey)) {
    showNotification('该主机已连接', 'warning')
    activeHostTab.value = hostKey
    return
  }

  try {
    addTerminalOutput(hostKey, `正在连接 ${config.host}...`, 'info')

    const response = await fetch(`${API_BASE}/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        host: config.host,
        port: config.port,
        username: config.username,
        password: config.password,
        type: connectionType.value
      })
    })

    const data = await response.json()

    if (data.status === 'success') {
      connectedHosts.value.push(hostKey)
      activeHostTab.value = hostKey
      addTerminalOutput(hostKey, `✅ 连接成功: ${config.host}`, 'success')
      addTerminalOutput(hostKey, `Session ID: ${data.session_id}`, 'info')
      showNotification('连接成功', 'success')
    } else {
      addTerminalOutput(hostKey, `❌ 连接失败: ${data.error}`, 'error')
      showNotification(`连接失败: ${data.error}`, 'error')
    }
  } catch (error) {
    const hostKey = `${connectionType.value[0]}${config.host}`
    addTerminalOutput(hostKey, `❌ 连接错误: ${error.message}`, 'error')
    showNotification(`连接错误: ${error.message}`, 'error')
  }
}

// Close host
const closeHost = (host) => {
  const index = connectedHosts.value.indexOf(host)
  if (index > -1) {
    connectedHosts.value.splice(index, 1)
    delete hostTerminals.value[host]

    if (activeHostTab.value === host) {
      activeHostTab.value = connectedHosts.value[0] || ''
    }
  }
}

onMounted(() => {
  // Initialization
})

onUnmounted(() => {
  // Cleanup
})
</script>

<style scoped>
.ssh-terminal-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.main-content {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  margin-top: 20px;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* Section */
.section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 15px;
}

/* Form */
.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

/* Connection Type */
.connection-type-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.radio-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 15px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
}

.radio-card input {
  display: none;
}

.radio-card.active {
  border-color: #6B5DD3;
  background: linear-gradient(135deg, rgba(107, 93, 211, 0.1) 0%, rgba(139, 127, 232, 0.1) 100%);
}

.radio-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.radio-name {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

/* Terminal Section */
.terminal-section {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin: 0;
  margin-bottom: 15px;
  flex-shrink: 0;
}

.terminal-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  flex: 1;
}

.terminal-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.terminal-window {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 15px;
  height: 705px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.terminal-line {
  padding: 2px 0;
  color: #d4d4d4;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.terminal-line.success {
  color: #4CAF50;
}

.terminal-line.error {
  color: #f44336;
}

.terminal-line.info {
  color: #2196F3;
}

.terminal-empty {
  color: #666;
  text-align: center;
  padding: 20px;
}

.host-tabs {
  display: flex;
  gap: 5px;
  margin-bottom: 15px;
  border-bottom: 2px solid #e0e0e0;
}

.host-tab {
  padding: 8px 16px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  cursor: pointer;
  font-size: 13px;
  color: #666;
  transition: all 0.3s;
  user-select: none;
}

.host-tab:hover {
  background: #e8e8e8;
  color: #333;
}

.host-tab.active {
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 100%);
  color: white;
  border-color: #6B5DD3;
  font-weight: 600;
}

/* Buttons */
.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(107, 93, 211, 0.4);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-full {
  width: 100%;
}

/* Notification */
.notification {
  position: fixed;
  top: 80px;
  right: 20px;
  padding: 12px 20px;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 1000;
}

.notification.success {
  background: linear-gradient(135deg, #27ae60, #2ecc71);
}

.notification.error {
  background: linear-gradient(135deg, #c0392b, #e74c3c);
}

.notification.info {
  background: linear-gradient(135deg, #2980b9, #3498db);
}

.notification.warning {
  background: linear-gradient(135deg, #f39c12, #f1c40f);
}

@media (max-width: 1024px) {
  .main-content {
    grid-template-columns: 1fr;
  }
}
</style>
