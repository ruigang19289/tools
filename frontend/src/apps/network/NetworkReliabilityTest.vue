<template>
  <div class="iperf3-page">
    <PageHeader
      icon="📡"
      title="带宽测试"
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
              v-model="hostsText"
              placeholder="192.168.1.1
192.168.1.2
192.168.1.3"
              rows="3"
            ></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>用户名:</label>
              <input type="text" v-model="config.username" placeholder="root">
            </div>
            <div class="form-group">
              <label>端口:</label>
              <input type="number" v-model="config.port" placeholder="5201">
            </div>
          </div>

          <div class="form-group">
            <label>密码:</label>
            <input type="password" v-model="config.password" placeholder="******">
          </div>

          <div class="form-group">
            <label>测试网段 (CIDR):</label>
            <input type="text" v-model="config.testCidr" placeholder="10.255.0.0/24">
          </div>

          <button class="btn btn-primary btn-full" @click="validateHosts" :disabled="!canValidate">
            验证连接
          </button>
        </div>

        <!-- Test Parameters and Type -->
        <div class="section">
          <h2 class="section-title">测试参数</h2>

          <div class="form-row-3">
            <div class="form-group">
              <label>时长 (秒):</label>
              <input type="number" v-model="config.duration" min="5" max="300">
            </div>
            <div class="form-group">
              <label>并行数:</label>
              <input type="number" v-model="config.parallel" min="1" max="64">
            </div>
            <div class="form-group">
              <label>端口:</label>
              <input type="number" v-model="config.port" min="1024" max="65535">
            </div>
          </div>

          <div class="test-types">
            <div
              class="test-type-card"
              :class="{ active: testType === 'one2one' }"
              @click="testType = 'one2one'"
            >
              <div class="test-type-icon">📡</div>
              <div class="test-type-name">One2One</div>
              <div class="test-type-desc">单服务器接收，其他服务器发送</div>
            </div>

            <div
              class="test-type-card"
              :class="{ active: testType === 'roundrobin' }"
              @click="testType = 'roundrobin'"
            >
              <div class="test-type-icon">🔄</div>
              <div class="test-type-name">RoundRobin</div>
              <div class="test-type-desc">所有服务器互相收发</div>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="section actions-section">
          <button
            class="btn btn-primary btn-full"
            @click="startTest"
            :disabled="!canStartTest || isTesting"
          >
            {{ isTesting ? '测试中...' : '开始测试' }}
          </button>

          <button
            v-if="isTesting"
            class="btn btn-danger btn-full"
            @click="stopTest"
          >
            停止测试
          </button>
        </div>

        <!-- Validation Results -->
        <div v-if="validationResults.length > 0" class="section">
          <h2 class="section-title">验证结果</h2>
          <div class="validation-results">
            <div
              v-for="(result, index) in validationResults"
              :key="index"
              :class="['validation-item', result.status]"
            >
              <span class="validation-icon">
                {{ result.status === 'success' ? '✅' : result.status === 'warning' ? '⚠️' : '❌' }}
              </span>
              <span class="validation-host">{{ result.host }}</span>
              <span class="validation-msg">{{ result.message }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Panel: Terminal Output -->
      <div class="right-panel">
        <div class="terminal-section">
          <div class="terminal-header">
            <span class="terminal-title">终端输出</span>
            <div class="terminal-controls">
              <button class="btn btn-compact" @click="clearTerminal">清空</button>
              <button class="btn btn-compact" @click="copyOutput">复制</button>
            </div>
          </div>
          <div class="terminal-window" ref="terminalWindow">
            <div
              v-for="(line, index) in terminalLines"
              :key="index"
              :class="['terminal-line', line.type]"
            >
              <span class="timestamp">[{{ line.time }}]</span>
              <span class="message">{{ line.message }}</span>
            </div>
            <div v-if="terminalLines.length === 0" class="terminal-empty">
              等待测试开始...
            </div>
          </div>
        </div>

        <!-- Results Summary -->
        <div v-if="testResults.length > 0" class="results-section">
          <h3 class="results-title">📊 测试结果汇总</h3>
          <table class="results-table">
            <thead>
              <tr>
                <th>发送端</th>
                <th>接收端</th>
                <th>带宽 (Gb/s)</th>
                <th>流数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(result, index) in testResults" :key="index">
                <td>{{ result.sender || result.client }}</td>
                <td>{{ result.receiver || result.server }}</td>
                <td class="bandwidth">{{ result.avg_gbps.toFixed(2) }}</td>
                <td>{{ result.streams }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td colspan="2"><strong>总计/平均</strong></td>
                <td class="bandwidth"><strong>{{ getTotalBandwidth().toFixed(2) }}</strong></td>
                <td></td>
              </tr>
            </tfoot>
          </table>
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
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/common/PageHeader.vue'

const router = useRouter()
const API_BASE = `/api/v1/perf/iperf3`

// Hosts text
const hostsText = ref('')

// Configuration
const config = reactive({
  username: 'root',
  password: '',
  testCidr: '',
  duration: 10,
  parallel: 1,
  port: 5201
})

// Test state
const testType = ref('one2one')
const isTesting = ref(false)
const currentTaskId = ref('')
const pollTimer = ref(null)

// Terminal output
const terminalLines = ref([])
const terminalWindow = ref(null)

// Results
const testResults = ref([])
const validationResults = ref([])

// Notification
const notification = reactive({
  show: false,
  message: '',
  type: 'info'
})

// Computed
const canValidate = computed(() => {
  const validHosts = getValidHosts()
  return validHosts.length > 0 && config.username && config.password
})

const canStartTest = computed(() => {
  const validHosts = getValidHosts()
  return validHosts.length >= 2 && config.username && config.password
})

// Get valid hosts
const getValidHosts = () => {
  return hostsText.value
    .split('\n')
    .map(h => h.trim())
    .filter(h => h)
}

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
const addTerminalLine = (type, message) => {
  const now = new Date()
  const time = now.toLocaleTimeString()
  terminalLines.value.push({ time, type, message })

  nextTick(() => {
    if (terminalWindow.value) {
      terminalWindow.value.scrollTop = terminalWindow.value.scrollHeight
    }
  })
}

// Clear terminal
const clearTerminal = () => {
  terminalLines.value = []
}

// Copy output
const copyOutput = () => {
  const text = terminalLines.value
    .map(line => `[${line.time}] ${line.message}`)
    .join('\n')
  navigator.clipboard.writeText(text)
  showNotification('输出已复制到剪贴板', 'success')
}

// Validate hosts
const validateHosts = async () => {
  const validHosts = getValidHosts()

  if (validHosts.length === 0) {
    showNotification('请至少添加两台主机', 'error')
    return
  }

  addTerminalLine('info', '开始验证主机连接...')

  try {
    const response = await fetch(`${API_BASE}/validate-hosts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hosts: validHosts,
        username: config.username,
        password: config.password
      })
    })

    const data = await response.json()

    if (data.status === 'success') {
      validationResults.value = data.results
      data.results.forEach(r => {
        const icon = r.status === 'success' ? '✅' : r.status === 'warning' ? '⚠️' : '❌'
        addTerminalLine(r.status === 'error' ? 'error' : 'info',
          `${icon} ${r.host}: ${r.message}`)
      })

      const successCount = data.results.filter(r => r.status === 'success').length
      const hasIperf3 = data.results.every(r => r.has_iperf3)

      if (successCount === validHosts.length) {
        if (hasIperf3) {
          showNotification(`所有主机连接成功，iperf3 已安装`, 'success')
        } else {
          showNotification(`所有主机连接成功，部分主机缺少 iperf3`, 'warning')
        }
      } else {
        showNotification(`部分主机连接失败`, 'error')
      }
    }
  } catch (error) {
    addTerminalLine('error', `验证错误: ${error.message}`)
    showNotification(`验证错误: ${error.message}`, 'error')
  }
}

// Start test
const startTest = async () => {
  const validHosts = getValidHosts()

  if (validHosts.length < 2) {
    showNotification('至少需要2台主机', 'error')
    return
  }

  isTesting.value = true
  testResults.value = []
  currentTaskId.value = ''

  const testName = testType.value === 'one2one' ? 'One2One' : 'RoundRobin'
  addTerminalLine('info', `========================================`)
  addTerminalLine('info', `开始 ${testName} 网络带宽测试`)
  addTerminalLine('info', `主机数: ${validHosts.length}, 时长: ${config.duration}s, 并行: ${config.parallel}`)
  addTerminalLine('info', `========================================`)

  try {
    const endpoint = testType.value === 'one2one' ? 'test-one2one' : 'test-roundrobin'
    const response = await fetch(`${API_BASE}/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hosts: validHosts,
        username: config.username,
        password: config.password,
        test_cidr: config.testCidr,
        duration: config.duration,
        parallel: config.parallel,
        port: config.port
      })
    })

    const data = await response.json()

    if (data.status === 'success') {
      currentTaskId.value = data.task_id
      startPolling()
      showNotification(`${testName} 测试已开始`, 'success')
    } else {
      addTerminalLine('error', `开始测试失败: ${data.error}`)
      isTesting.value = false
      showNotification(`开始测试失败: ${data.error}`, 'error')
    }
  } catch (error) {
    addTerminalLine('error', `开始测试错误: ${error.message}`)
    isTesting.value = false
    showNotification(`开始测试错误: ${error.message}`, 'error')
  }
}

// Stop test
const stopTest = async () => {
  if (currentTaskId.value) {
    try {
      await fetch(`${API_BASE}/test-stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: currentTaskId.value })
      })
    } catch (e) {
      // Ignore errors
    }
  }

  isTesting.value = false
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
  addTerminalLine('warning', '测试已手动停止')
  showNotification('测试已停止', 'info')
}

// Poll for results
const startPolling = () => {
  pollTimer.value = setInterval(async () => {
    if (!currentTaskId.value) {
      clearInterval(pollTimer.value)
      return
    }

    try {
      const response = await fetch(`${API_BASE}/test-output?task_id=${currentTaskId.value}`)
      const data = await response.json()

      if (data.status === 'success') {
        // Add new output lines
        const lastIndex = terminalLines.value.length
        data.output.forEach((line, idx) => {
          if (idx >= lastIndex) {
            terminalLines.value.push(line)
          }
        })

        // Update results
        if (data.results && data.results.length > 0) {
          testResults.value = data.results
        }

        // Check if completed
        if (data.status === 'completed' || data.status === 'error' || data.status === 'stopped') {
          isTesting.value = false
          clearInterval(pollTimer.value)
          pollTimer.value = null

          if (data.status === 'completed') {
            addTerminalLine('success', '测试已完成')
            showNotification('测试完成', 'success')
          }
        }
      }
    } catch (error) {
      console.error('Polling error:', error)
    }
  }, 1000)
}

// Get total bandwidth
const getTotalBandwidth = () => {
  if (testResults.value.length === 0) return 0
  return testResults.value.reduce((sum, r) => sum + r.avg_gbps, 0)
}

// Cleanup on unmount
onUnmounted(() => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
  }
})
</script>

<style scoped>
.iperf3-page {
  min-height: 100vh;
  padding: 20px;
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 50%, #9B8FF8 100%);
  position: relative;
}

.iperf3-page::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 35px,
    rgba(255, 255, 255, 0.05) 35px,
    rgba(255, 255, 255, 0.05) 70px
  );
  pointer-events: none;
  z-index: 0;
}

.iperf3-page > * {
  position: relative;
  z-index: 1;
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

.form-group textarea {
  resize: vertical;
  min-height: 60px;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #6B5DD3;
  box-shadow: 0 0 0 3px rgba(107, 93, 211, 0.1);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.form-row-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
  margin-bottom: 15px;
}

.hosts-section {
  margin: 15px 0;
}

.hosts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-weight: 500;
  color: #333;
}

.btn-small {
  padding: 4px 8px;
  font-size: 12px;
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 100%);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.host-inputs {
  max-height: 150px;
  overflow-y: auto;
}

.host-input-row {
  display: flex;
  gap: 5px;
  margin-bottom: 5px;
}

.host-input-row input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.btn-remove {
  width: 24px;
  height: 24px;
  background: #f44336;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-full {
  width: 100%;
}

.btn-large {
  padding: 15px;
  font-size: 16px;
}

.test-types {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 15px;
}

.test-type-card {
  padding: 15px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
}

.test-type-card:hover {
  border-color: #6B5DD3;
}

.test-type-card.active {
  border-color: #6B5DD3;
  background: rgba(107, 93, 211, 0.1);
}

.test-type-icon {
  font-size: 28px;
  margin-bottom: 8px;
}

.test-type-name {
  font-weight: 600;
  color: #333;
  margin-bottom: 5px;
}

.test-type-desc {
  font-size: 11px;
  color: #999;
}

.actions-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.validation-results {
  max-height: 200px;
  overflow-y: auto;
}

.validation-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
  margin-bottom: 5px;
  font-size: 13px;
}

.validation-item.success {
  background: #e8f5e9;
}

.validation-item.warning {
  background: #fff3e0;
}

.validation-item.error {
  background: #ffebee;
}

.validation-host {
  font-weight: 600;
  color: #333;
  min-width: 100px;
}

.validation-msg {
  color: #666;
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
  flex: 1;
  display: flex;
  flex-direction: column;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #6B5DD3;
}

.terminal-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.terminal-controls {
  display: flex;
  gap: 8px;
}

.terminal-window {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 15px;
  flex: 1;
  min-height: 200px;
  overflow-y: auto;
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.terminal-line {
  padding: 2px 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.terminal-line .timestamp {
  color: #666;
  margin-right: 8px;
}

.terminal-line.info .message {
  color: #2196F3;
}

.terminal-line.success .message {
  color: #4CAF50;
}

.terminal-line.error .message {
  color: #f44336;
}

.terminal-line.warning .message {
  color: #ff9800;
}

.terminal-empty {
  color: #666;
  text-align: center;
  padding: 20px;
}

.results-section {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.results-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 15px;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
}

.results-table th,
.results-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.results-table th {
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 100%);
  color: white;
  font-weight: 600;
}

.results-table .bandwidth {
  color: #4CAF50;
  font-weight: 600;
  font-family: monospace;
}

.results-table tfoot td {
  background: #f5f5f5;
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

.notification.warning {
  background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
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
