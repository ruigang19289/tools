<template>
  <div class="connection-test-page">
    <PageHeader
      icon="🔌"
      title="持续网络测试"
    />

    <!-- Main Content -->
    <div class="main-content">
      <!-- Left Panel: Configuration -->
      <div class="left-panel">
        <!-- Host Configuration -->
        <div class="section">
          <h2 class="section-title">主机配置</h2>

          <div class="form-group">
            <label>远程主机 (每行一个):</label>
            <textarea
              v-model="ipListText"
              placeholder="192.168.1.1
192.168.1.2
192.168.1.3"
              rows="3"
            ></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>端口:</label>
              <input type="number" v-model="config.port" placeholder="22">
            </div>
            <div class="form-group">
              <label>用户名:</label>
              <input type="text" v-model="config.username" placeholder="root">
            </div>
          </div>

          <div class="form-group">
            <label>密码:</label>
            <input type="password" v-model="config.password" placeholder="******">
          </div>
        </div>

        <!-- Test Parameters -->
        <div class="section">
          <h2 class="section-title">测试参数</h2>

          <div class="form-row">
            <div class="form-group">
              <label>Ping 间隔 (秒):</label>
              <input type="number" v-model="config.pingInterval" min="1" max="60">
            </div>
            <div class="form-group">
              <label>SSH 间隔 (秒):</label>
              <input type="number" v-model="config.sshInterval" min="5" max="300">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>超时 (秒):</label>
              <input type="number" v-model="config.timeout" min="1" max="30">
            </div>
            <div class="form-group">
              <label>包大小 (字节):</label>
              <input type="number" v-model="config.packetSize" min="56" max="1472">
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="section">
          <h2 class="section-title">测试控制</h2>

          <div class="action-buttons">
            <button
              class="btn btn-primary btn-full"
              @click="togglePingTest"
              :disabled="!canStartPing || (isPingRunning && isSshRunning)"
            >
              {{ isPingRunning ? '停止 Ping' : '开始 Ping' }}
            </button>

            <button
              class="btn btn-primary btn-full"
              @click="toggleSshTest"
              :disabled="!canStartSsh || (isPingRunning && isSshRunning)"
            >
              {{ isSshRunning ? '停止 SSH' : '开始 SSH' }}
            </button>

            <button
              class="btn btn-warning btn-full"
              @click="toggleAllTests"
              :disabled="!canStartPing || !canStartSsh"
            >
              {{ allRunning ? '全部停止' : '全部开始' }}
            </button>
          </div>
        </div>

        <!-- Statistics -->
        <div class="section">
          <h2 class="section-title">实时统计</h2>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon">📊</div>
              <div class="stat-info">
                <div class="stat-value">{{ ipList.length }}</div>
                <div class="stat-label">总主机</div>
              </div>
            </div>

            <div class="stat-card success">
              <div class="stat-icon">✅</div>
              <div class="stat-info">
                <div class="stat-value">{{ allStats.online }}</div>
                <div class="stat-label">在线/成功</div>
              </div>
            </div>

            <div class="stat-card warning">
              <div class="stat-icon">⏰</div>
              <div class="stat-info">
                <div class="stat-value">{{ allStats.timeout }}</div>
                <div class="stat-label">超时</div>
              </div>
            </div>

            <div class="stat-card error">
              <div class="stat-icon">❌</div>
              <div class="stat-info">
                <div class="stat-value">{{ allStats.offline + allStats.failed }}</div>
                <div class="stat-label">离线/失败</div>
              </div>
            </div>
          </div>

          <div class="test-status">
            <span class="status-badge" :class="{ active: isPingRunning }">
              Ping: {{ pingTestCount }} 次
            </span>
            <span class="status-badge" :class="{ active: isSshRunning }">
              SSH: {{ sshTestCount }} 次
            </span>
          </div>
        </div>
      </div>

      <!-- Right Panel: Terminals -->
      <div class="right-panel">
        <!-- Ping Terminal -->
        <div class="terminal-section ping-terminal">
          <div class="terminal-header ping-header">
            <div class="terminal-title-group">
              <span class="terminal-title">Ping终端输出</span>
            </div>
            <div class="terminal-controls">
              <span class="terminal-stat">
                成功: {{ pingStats.online }} | 超时: {{ pingStats.timeout }} | 失败: {{ pingStats.offline }}
              </span>
              <button class="btn btn-compact" @click="clearPingTerminal">清空</button>
              <button class="btn btn-compact" @click="downloadPingOutput">下载</button>
            </div>
          </div>
          <div class="terminal-window" ref="pingTerminalWindow">
            <div
              v-for="(line, index) in pingLines"
              :key="'ping-' + index"
              :class="['terminal-line', line.type]"
            >
              <span class="timestamp">[{{ line.time }}]</span>
              <span class="count">#{{ line.count }}</span>
              <span class="ip">{{ line.ip }}</span>
              <span class="message">{{ line.message }}</span>
            </div>
            <div v-if="pingLines.length === 0" class="terminal-empty">
              点击"开始 Ping"启动测试...
            </div>
          </div>
        </div>

        <!-- SSH Terminal -->
        <div class="terminal-section ssh-terminal">
          <div class="terminal-header ssh-header">
            <div class="terminal-title-group">
              <span class="terminal-title">SSH终端输出</span>
            </div>
            <div class="terminal-controls">
              <span class="terminal-stat">
                成功: {{ sshStats.success }} | 超时: {{ sshStats.timeout }} | 失败: {{ sshStats.failed }}
              </span>
              <button class="btn btn-compact" @click="clearSshTerminal">清空</button>
              <button class="btn btn-compact" @click="downloadSshOutput">下载</button>
            </div>
          </div>
          <div class="terminal-window" ref="sshTerminalWindow">
            <div
              v-for="(line, index) in sshLines"
              :key="'ssh-' + index"
              :class="['terminal-line', line.type]"
            >
              <span class="timestamp">[{{ line.time }}]</span>
              <span class="count">#{{ line.count }}</span>
              <span class="ip">{{ line.ip }}</span>
              <span class="message">{{ line.message }}</span>
            </div>
            <div v-if="sshLines.length === 0" class="terminal-empty">
              点击"开始 SSH"启动测试...
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Notification -->
    <div class="notification" :class="[notification.type]" v-if="notification.show">
      {{ notification.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/common/PageHeader.vue'

const router = useRouter()
const API_BASE = `/api/v1/network/connection-test`

// IP List
const ipListText = ref('')

// Configuration
const config = reactive({
  username: '',
  password: '',
  port: 22,
  pingInterval: 1,
  sshInterval: 10,
  timeout: 5,
  packetSize: 56
})

// Test state
const isPingRunning = ref(false)
const isSshRunning = ref(false)
const pingTaskId = ref('')
const sshTaskId = ref('')
const pingTestCount = ref(0)
const sshTestCount = ref(0)
const pollTimer = ref(null)

// Terminal lines
const pingLines = ref([])
const sshLines = ref([])
const pingTerminalWindow = ref(null)
const sshTerminalWindow = ref(null)
const lastPingCount = ref(0)
const lastSshCount = ref(0)

// Notification
const notification = reactive({
  show: false,
  message: '',
  type: 'info'
})

// Computed
const ipList = computed(() => {
  return ipListText.value
    .split('\n')
    .map(ip => ip.trim())
    .filter(ip => ip)
})

const canStartPing = computed(() => ipList.value.length > 0)
const canStartSsh = computed(() => ipList.value.length > 0 && config.username && config.password)
const allRunning = computed(() => isPingRunning.value && isSshRunning.value)

const pingStats = computed(() => {
  if (pingTaskId.value && activePingStats.value) {
    return activePingStats.value
  }
  return { online: 0, offline: 0, timeout: 0 }
})

const sshStats = computed(() => {
  if (sshTaskId.value && activeSshStats.value) {
    return activeSshStats.value
  }
  return { success: 0, failed: 0, timeout: 0 }
})

const allStats = computed(() => ({
  online: pingStats.value.online,
  timeout: pingStats.value.timeout + sshStats.value.timeout,
  offline: pingStats.value.offline,
  failed: sshStats.value.failed
}))

// Active stats storage
const activePingStats = ref({ online: 0, offline: 0, timeout: 0 })
const activeSshStats = ref({ success: 0, failed: 0, timeout: 0 })

// Show notification
const showNotification = (message, type = 'info') => {
  notification.message = message
  notification.type = type
  notification.show = true
  setTimeout(() => {
    notification.show = false
  }, 3000)
}

// Add terminal line
const addPingLine = (line) => {
  pingLines.value.push(line)
  if (pingLines.value.length > 200) {
    pingLines.value = pingLines.value.slice(-200)
  }
  scrollPingTerminal()
}

const addSshLine = (line) => {
  sshLines.value.push(line)
  if (sshLines.value.length > 200) {
    sshLines.value = sshLines.value.slice(-200)
  }
  scrollSshTerminal()
}

// Scroll terminal
const scrollPingTerminal = () => {
  nextTick(() => {
    if (pingTerminalWindow.value) {
      pingTerminalWindow.value.scrollTop = pingTerminalWindow.value.scrollHeight
    }
  })
}

const scrollSshTerminal = () => {
  nextTick(() => {
    if (sshTerminalWindow.value) {
      sshTerminalWindow.value.scrollTop = sshTerminalWindow.value.scrollHeight
    }
  })
}

// Clear terminals
const clearPingTerminal = () => {
  pingLines.value = []
  activePingStats.value = { online: 0, offline: 0, timeout: 0 }
  pingTestCount.value = 0
  lastPingCount.value = 0
}

const clearSshTerminal = () => {
  sshLines.value = []
  activeSshStats.value = { success: 0, failed: 0, timeout: 0 }
  sshTestCount.value = 0
  lastSshCount.value = 0
}

// 下载 Ping 输出
const downloadPingOutput = () => {
  if (pingLines.value.length === 0) {
    alert('没有可下载的输出')
    return
  }

  const content = pingLines.value.map(line => {
    return `[${line.time}] #${line.count} ${line.ip} ${line.message}`
  }).join('\n')

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
  link.download = `ping_test_output_${timestamp}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

// 下载 SSH 输出
const downloadSshOutput = () => {
  if (sshLines.value.length === 0) {
    alert('没有可下载的输出')
    return
  }

  const content = sshLines.value.map(line => {
    return `[${line.time}] #${line.count} ${line.ip} ${line.message}`
  }).join('\n')

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
  link.download = `ssh_test_output_${timestamp}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

// Start/Stop Ping test
const togglePingTest = async () => {
  if (isPingRunning.value) {
    await stopPingTest()
  } else {
    await startPingTest()
  }
}

const startPingTest = async () => {
  try {
    const response = await fetch(`${API_BASE}/ping-start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ips: ipList.value,
        interval: config.pingInterval,
        timeout: config.timeout,
        packet_size: config.packetSize
      })
    })

    const data = await response.json()
    if (data.status === 'success') {
      pingTaskId.value = data.task_id
      isPingRunning.value = true
      lastPingCount.value = 0
      showNotification('Ping 测试已启动', 'success')
      startPolling()
    } else {
      showNotification(`启动失败: ${data.error}`, 'error')
    }
  } catch (error) {
    showNotification(`错误: ${error.message}`, 'error')
  }
}

const stopPingTest = async () => {
  if (pingTaskId.value) {
    await fetch(`${API_BASE}/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: pingTaskId.value })
    })
  }
  isPingRunning.value = false
  pingTaskId.value = ''
  showNotification('Ping 测试已停止', 'info')
}

// Start/Stop SSH test
const toggleSshTest = async () => {
  if (isSshRunning.value) {
    await stopSshTest()
  } else {
    await startSshTest()
  }
}

const startSshTest = async () => {
  try {
    const response = await fetch(`${API_BASE}/ssh-start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ips: ipList.value,
        username: config.username,
        password: config.password,
        interval: config.sshInterval,
        timeout: config.timeout
      })
    })

    const data = await response.json()
    if (data.status === 'success') {
      sshTaskId.value = data.task_id
      isSshRunning.value = true
      lastSshCount.value = 0
      showNotification('SSH 测试已启动', 'success')
      startPolling()
    } else {
      showNotification(`启动失败: ${data.error}`, 'error')
    }
  } catch (error) {
    showNotification(`错误: ${error.message}`, 'error')
  }
}

const stopSshTest = async () => {
  if (sshTaskId.value) {
    await fetch(`${API_BASE}/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: sshTaskId.value })
    })
  }
  isSshRunning.value = false
  sshTaskId.value = ''
  showNotification('SSH 测试已停止', 'info')
}

// Toggle all tests
const toggleAllTests = async () => {
  if (allRunning.value) {
    await Promise.all([stopPingTest(), stopSshTest()])
  } else {
    await Promise.all([startPingTest(), startSshTest()])
  }
}

// Polling
const startPolling = () => {
  if (pollTimer.value) return

  pollTimer.value = setInterval(async () => {
    const promises = []

    if (isPingRunning.value && pingTaskId.value) {
      promises.push(
        fetch(`${API_BASE}/output?task_id=${pingTaskId.value}`)
          .then(r => r.json())
          .then(data => {
            if (data.status === 'success' || data.status === 'running') {
              pingTestCount.value = data.count
              activePingStats.value = data.stats

              if (data.output && data.output.length > 0) {
                data.output.forEach(line => {
                  if (line.count > lastPingCount.value) {
                    addPingLine({
                      time: line.time.split(' ')[1],
                      type: line.type,
                      ip: line.ip,
                      count: line.count,
                      message: line.message
                    })
                    lastPingCount.value = Math.max(lastPingCount.value, line.count)
                  }
                })
              }
            }
          })
          .catch(err => {
            console.error('Ping fetch error:', err)
          })
      )
    }

    if (isSshRunning.value && sshTaskId.value) {
      promises.push(
        fetch(`${API_BASE}/output?task_id=${sshTaskId.value}`)
          .then(r => r.json())
          .then(data => {
            if (data.status === 'success' || data.status === 'running') {
              sshTestCount.value = data.count
              activeSshStats.value = data.stats

              if (data.output && data.output.length > 0) {
                data.output.forEach(line => {
                  if (line.count > lastSshCount.value) {
                    addSshLine({
                      time: line.time.split(' ')[1],
                      type: line.type,
                      ip: line.ip,
                      count: line.count,
                      message: line.message
                    })
                    lastSshCount.value = Math.max(lastSshCount.value, line.count)
                  }
                })
              }
            }
          })
          .catch(err => {
            console.error('SSH fetch error:', err)
          })
      )
    }

    await Promise.all(promises)
  }, 1000)
}

// Cleanup
onUnmounted(() => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
  }
  // 停止所有测试
  if (isPingRunning.value) stopPingTest()
  if (isSshRunning.value) stopSshTest()
})
</script>

<script>
import { nextTick } from 'vue'
</script>

<style scoped>
.connection-test-page {
  min-height: 100vh;
  padding: 20px;
  position: relative;
}

.main-content {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  min-height: calc(100vh - 140px);
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.section {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #6B5DD3;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  color: #666;
  font-size: 12px;
  margin-bottom: 4px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  font-family: monospace;
  transition: all 0.3s;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #6B5DD3;
  box-shadow: 0 0 0 3px rgba(107, 93, 211, 0.1);
}

.form-group textarea {
  resize: vertical;
  min-height: 60px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 8px;
}

.btn-compact {
  padding: 6px 12px !important;
  font-size: 12px !important;
  width: auto !important;
}

.btn-full {
  width: 100%;
}

.btn-small {
  padding: 4px 8px;
  font-size: 12px;
  background: #e0e0e0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 15px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
  border-left: 4px solid #6B5DD3;
}

.stat-card.success {
  border-left-color: #4CAF50;
}

.stat-card.warning {
  border-left-color: #ff9800;
}

.stat-card.error {
  border-left-color: #f44336;
}

.stat-icon {
  font-size: 24px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #333;
}

.stat-label {
  font-size: 12px;
  color: #999;
}

.test-status {
  display: flex;
  gap: 10px;
}

.status-badge {
  padding: 4px 10px;
  background: #e0e0e0;
  border-radius: 20px;
  font-size: 12px;
  color: #666;
}

.status-badge.active {
  background: #4CAF50;
  color: white;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.terminal-section {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

/* Ping 终端区域 - 和主机配置+测试参数对齐 */
.ping-terminal {
  height: 555px;
}

/* SSH 终端区域 - 和实时统计底部对齐(整个界面最底部) */
.ssh-terminal {
  height: 540px;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin: 0;
  margin-bottom: 15px;
}

.terminal-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  flex: 1;
}

.ping-header .terminal-title-group {
  border-bottom: none;
}

.ssh-header .terminal-title-group {
  border-bottom: none;
}

.terminal-icon {
  font-size: 20px;
}

.terminal-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  line-height: 1.2;
}

.terminal-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.terminal-stat {
  font-size: 12px;
  color: #666;
  font-family: monospace;
}

.terminal-window {
  flex: 1;
  background: #1e1e1e;
  border-radius: 8px;
  padding: 15px;
  overflow-y: auto;
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
}

/* 移除之前的特殊样式 */

.terminal-line {
  padding: 2px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.terminal-line .timestamp {
  color: #666;
  margin-right: 8px;
}

.terminal-line .count {
  color: #ff9800;
  margin-right: 8px;
}

.terminal-line .ip {
  color: #2196F3;
  font-weight: 600;
  margin-right: 8px;
  min-width: 100px;
}

.terminal-line.success .message {
  color: #4CAF50;
}

.terminal-line.error .message {
  color: #f44336;
}

.terminal-line.timeout .message {
  color: #ff9800;
}

.terminal-empty {
  color: #666;
  text-align: center;
  padding: 20px;
}

.notification {
  position: fixed;
  top: 80px;
  right: 20px;
  padding: 15px 20px;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 1000;
  animation: slideIn 0.3s ease-out;
}

.notification.success {
  background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
}

.notification.error {
  background: linear-gradient(135deg, #f44336 0%, #da190b 100%);
}

.notification.info {
  background: linear-gradient(135deg, #2196F3 0%, #0b7dda 100%);
}

@keyframes slideIn {
  from {
    transform: translateX(400px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@media (max-width: 1024px) {
  .main-content {
    grid-template-columns: 1fr;
  }

  .right-panel {
    order: -1;
  }
}
</style>
