<template>
  <div class="fio-page">
    <PageHeader
      icon="📊"
      title="FIO 性能测试"
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

          <button class="btn btn-primary btn-full" @click="validateHosts" :disabled="!canValidate">
            验证连接
          </button>

          <div v-if="validationResults.length > 0" class="validation-summary">
            <span class="badge success" v-if="validationResults.every(r => r.status === 'success')">
              ✅ 全部连接成功
            </span>
            <span class="badge warning" v-else-if="validationResults.some(r => r.status === 'success')">
              ⚠️ 部分成功 ({{ validationResults.filter(r => r.status === 'success').length }}/{{ getValidHosts().length }})
            </span>
            <span class="badge error" v-else>
              ❌ 连接失败
            </span>
          </div>
        </div>

        <!-- Test Type -->
        <div class="section">
          <h2 class="section-title">测试类型</h2>

          <div class="test-type-grid">
            <label class="radio-card" :class="{ active: params.rw === 'randread' }">
              <input type="radio" v-model="params.rw" value="randread">
              <span class="radio-icon">📖</span>
              <span class="radio-name">随机读</span>
            </label>
            <label class="radio-card" :class="{ active: params.rw === 'randwrite' }">
              <input type="radio" v-model="params.rw" value="randwrite">
              <span class="radio-icon">📝</span>
              <span class="radio-name">随机写</span>
            </label>
            <label class="radio-card" :class="{ active: params.rw === 'randrw' }">
              <input type="radio" v-model="params.rw" value="randrw">
              <span class="radio-icon">🔄</span>
              <span class="radio-name">混合读写</span>
            </label>
            <label class="radio-card" :class="{ active: params.rw === 'read' }">
              <input type="radio" v-model="params.rw" value="read">
              <span class="radio-icon">📑</span>
              <span class="radio-name">顺序读</span>
            </label>
            <label class="radio-card" :class="{ active: params.rw === 'write' }">
              <input type="radio" v-model="params.rw" value="write">
              <span class="radio-icon">✏️</span>
              <span class="radio-name">顺序写</span>
            </label>
          </div>

          <div v-if="params.rw === 'randrw'" class="form-group">
            <label>读写比例 (读% / 写%):</label>
            <div class="mix-slider">
              <input type="range" v-model="params.rwmixread" min="10" max="90">
              <span class="mix-label">{{ params.rwmixread }}% / {{ 100 - params.rwmixread }}%</span>
            </div>
          </div>
        </div>
        <!-- Test Engine -->
        <div class="section">
          <h2 class="section-title">测试引擎</h2>

          <div class="test-type-grid">
            <label class="radio-card" :class="{ active: params.ioengine === 'libaio' }">
              <input type="radio" v-model="params.ioengine" value="libaio">
              <span class="radio-icon">⚙️</span>
              <span class="radio-name">libaio</span>
            </label>
            <label class="radio-card" :class="{ active: params.ioengine === 'rbd' }">
              <input type="radio" v-model="params.ioengine" value="rbd">
              <span class="radio-icon">💾</span>
              <span class="radio-name">rbd</span>
            </label>
          </div>
        </div>

        <!-- Test Parameters -->
        <div class="section">
          <h2 class="section-title">测试参数</h2>

          <!-- RBD: 卷名称和测试大小在同一行 -->
          <div v-if="params.ioengine === 'rbd'" class="form-row">
            <div class="form-group">
              <label>卷名称:</label>
              <input type="text" v-model="params.filename" placeholder="rbdtest1">
            </div>
            <div class="form-group">
              <label>测试大小:</label>
              <input type="text" v-model="params.size" placeholder="100G">
            </div>
          </div>

          <!-- libaio: 卷名称和测试大小各占一行，使用占位符 -->
          <template v-else>
            <div class="form-row">
              <div class="form-group">
                <label>卷名称:</label>
                <input type="text" v-model="params.filename" placeholder="/dev/sdb">
              </div>
              <div class="form-group">
                <!-- 占位符 -->
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>测试大小:</label>
                <input type="text" v-model="params.size" placeholder="100G">
              </div>
              <div class="form-group">
                <!-- 占位符 -->
              </div>
            </div>
          </template>

          <div v-if="params.ioengine === 'rbd'" class="form-group">
            <label>存储池名称:</label>
            <input type="text" v-model="params.pool" placeholder="pool-rbdtest1">
          </div>

          <div class="params-grid">
            <div class="form-group">
              <label>块大小:</label>
              <select v-model="params.bs">
                <option value="4k">4 KB</option>
                <option value="8k">8 KB</option>
                <option value="16k">16 KB</option>
                <option value="32k">32 KB</option>
                <option value="64k">64 KB</option>
                <option value="128k">128 KB</option>
                <option value="256k">256 KB</option>
                <option value="512k">512 KB</option>
                <option value="1m">1 MB</option>
                <option value="4m">4 MB</option>
                <option value="10m">10 MB</option>
              </select>
            </div>

            <div class="form-group">
              <label>IO 深度:</label>
              <select v-model="params.iodepth">
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="4">4</option>
                <option value="8">8</option>
                <option value="16">16</option>
                <option value="32">32</option>
                <option value="64">64</option>
                <option value="128">128</option>
                <option value="256">256</option>
              </select>
            </div>

            <div class="form-group">
              <label>线程数:</label>
              <select v-model="params.numjobs">
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="4">4</option>
                <option value="8">8</option>
                <option value="16">16</option>
                <option value="32">32</option>
                <option value="64">64</option>
                <option value="128">128</option>
                <option value="256">256</option>
              </select>
            </div>

            <div class="form-group">
              <label>测试时长 (秒):</label>
              <input type="number" v-model="params.runtime" min="10" max="3600">
            </div>

            <div class="form-group">
              <label>CPU 核心:</label>
              <input type="text" v-model="params.cpus_allowed" placeholder="0-7">
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="section actions-section">
          <button
            class="btn btn-primary btn-full"
            @click="startTest"
            :disabled="!canStart || isTesting"
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
      </div>

      <!-- Right Panel: Visualization -->
      <div class="right-panel">
        <!-- Top Row: Summary Cards + Bandwidth Chart -->
        <div class="top-row">
          <!-- Summary Cards (2x2 grid) -->
          <div class="summary-cards">
            <div class="card">
              <div class="card-icon">⚡</div>
              <div class="card-content">
                <div class="card-label">平均 I/O 速率</div>
                <div class="card-value">{{ avgIops }}</div>
                <div class="card-unit">IOPS</div>
              </div>
            </div>
            <div class="card">
              <div class="card-icon">📈</div>
              <div class="card-content">
                <div class="card-label">平均吞吐量</div>
                <div class="card-value">{{ avgBw }}</div>
                <div class="card-unit">MB/s</div>
              </div>
            </div>
            <div class="card">
              <div class="card-icon">⏱️</div>
              <div class="card-content">
                <div class="card-label">平均响应时间</div>
                <div class="card-value">{{ avgLat }}</div>
                <div class="card-unit">ms</div>
              </div>
            </div>
            <div class="card card-empty">
              <div class="card-icon">⏰</div>
              <div class="card-content">
                <div class="card-label">运行时长</div>
                <div class="card-value">{{ elapsedTime }}</div>
                <div class="card-unit"></div>
              </div>
            </div>
          </div>

          <!-- Bandwidth Chart -->
          <div class="chart-wrapper">
            <h3>吞吐量 (MB/s)</h3>
            <canvas ref="bwChart"></canvas>
          </div>
        </div>

        <!-- Middle Row: IOPS Chart + Latency Chart -->
        <div class="middle-row">
          <div class="chart-wrapper">
            <h3>I/O 速率 (IOPS)</h3>
            <canvas ref="iopsChart"></canvas>
          </div>
          <div class="chart-wrapper">
            <h3>响应时间 (ms)</h3>
            <canvas ref="latChart"></canvas>
          </div>
        </div>

        <!-- Terminal Output -->
        <div class="terminal-section">
          <div class="terminal-header">
            <div class="terminal-title-group">
              <span class="terminal-title">终端输出</span>
            </div>
            <div class="terminal-controls">
              <button class="btn btn-compact" @click="clearOutput">清空</button>
              <button class="btn btn-compact" @click="downloadOutput">下载</button>
            </div>
          </div>

          <!-- Progress Bar -->
          <div v-if="isTesting" class="progress-container">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <div class="progress-text">{{ elapsedTime }} / {{ params.runtime }}s ({{ progressPercent.toFixed(0) }}%)</div>
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
            </div>
          </div>

          <div class="terminal-window" ref="terminalWindow">
            <div v-if="getCurrentTerminalLines().length === 0" class="terminal-empty">
              配置参数后点击"开始测试"...
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
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch, toRaw } from 'vue'
import Chart from 'chart.js/auto'
import PageHeader from '@/components/common/PageHeader.vue'

const API_BASE = `/api/v1/perf/fio`

// WebSocket
let ws = null
const wsConnected = ref(false)

// Hosts text
const hostsText = ref('')

// Configuration
const config = reactive({
  username: 'root',
  password: '',
  port: 22
})

// Test parameters
const params = reactive({
  rw: 'randread',
  rwmixread: 70,
  bs: '4k',
  iodepth: 64,
  numjobs: 4,
  runtime: 60,
  ioengine: 'libaio',
  filename: '/dev/sdb',
  pool: 'pool-rbdtest1',
  size: '100G',
  cpus_allowed: ''
})

// RW labels
const rwLabels = {
  randread: '随机读',
  randwrite: '随机写',
  randrw: '混合读写',
  read: '顺序读',
  write: '顺序写'
}

// Test state
const isTesting = ref(false)
const testCompleted = ref(false)
const taskId = ref('')
const pollTimer = ref(null)
const elapsedSeconds = ref(0)

// Stats
const currentStats = reactive({ iops: 0, bw: 0, lat: 0 })
const avgIops = ref('--')
const avgBw = ref('--')
const avgLat = ref('--')
const maxStats = reactive({ iops: 0, bw: 0, lat: 0 })
const minStats = reactive({ iops: 999999999, bw: 999999999, lat: 999999999 })
const finalStats = reactive({ iops: 0, bw: 0, lat: 0 })

// 多主机统计数据收集
const hostStats = ref({}) // 存储每个主机的最新统计数据
let statsAggregationTimer = null // 聚合定时器

// Chart data
const iopsChart = ref(null)
const bwChart = ref(null)
const latChart = ref(null)
let charts = { iops: null, bw: null, lat: null }
const chartData = reactive({
  iops: [],
  bw: [],
  lat: [],
  labels: []
})

// Terminal
const terminalLines = ref([])
const terminalWindow = ref(null)
const hostTerminals = ref({}) // 每个主机的独立终端输出
const activeHostTab = ref('') // 当前激活的主机标签

// Validation
const validationResults = ref([])
const connectedHosts = ref([])

// Notification
const notification = reactive({
  show: false,
  message: '',
  type: 'info'
})

// Watch ioengine changes to update filename default
watch(() => params.ioengine, (newEngine) => {
  if (newEngine === 'rbd') {
    if (params.filename === '/dev/sdb' || !params.filename) {
      params.filename = 'rbdtest1'
    }
  } else {
    if (params.filename === 'rbdtest1' || !params.filename) {
      params.filename = '/dev/sdb'
    }
  }
})

// Computed
const canValidate = computed(() => {
  const validHosts = getValidHosts()
  return validHosts.length > 0 && config.username && config.password
})

const canStart = computed(() => {
  const validHosts = getValidHosts()
  return validHosts.length > 0 && validationResults.value.length > 0 &&
    validationResults.value.every(r => r.status === 'success' || r.status === 'warning')
})

const elapsedTime = computed(() => {
  const mins = Math.floor(elapsedSeconds.value / 60)
  const secs = elapsedSeconds.value % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
})

const progressPercent = computed(() => {
  return Math.min(100, (elapsedSeconds.value / params.runtime) * 100)
})

// Get valid hosts
const getValidHosts = () => {
  return hostsText.value
    .split('\n')
    .map(h => h.trim())
    .filter(h => h)
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

// Add terminal output
const addTerminalLine = (type, text, host = null) => {
  if (host && hostTerminals.value[host]) {
    // 添加到特定主机的终端
    hostTerminals.value[host].push({ type, text })
  } else {
    // 添加到通用终端（用于非主机特定的消息）
    terminalLines.value.push({ type, text })
  }

  nextTick(() => {
    if (terminalWindow.value) {
      terminalWindow.value.scrollTop = terminalWindow.value.scrollHeight
    }
  })
}

const clearOutput = () => {
  if (activeHostTab.value && hostTerminals.value[activeHostTab.value]) {
    hostTerminals.value[activeHostTab.value] = []
  } else {
    terminalLines.value = []
  }
}

const downloadOutput = () => {
  const lines = getCurrentTerminalLines()
  if (lines.length === 0) {
    alert('没有可下载的输出')
    return
  }

  const content = lines.map(line => line.text).join('\n')
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const hostname = activeHostTab.value || 'all'
  link.download = `fio_test_output_${hostname}_${new Date().toISOString().replace(/[:.]/g, '-')}.txt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// 获取当前激活标签的终端输出
const getCurrentTerminalLines = () => {
  if (activeHostTab.value && hostTerminals.value[activeHostTab.value]) {
    return hostTerminals.value[activeHostTab.value]
  }
  return terminalLines.value
}

// WebSocket functions
const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/v1/perf/fio/ws`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    wsConnected.value = true
    console.log('FIO WebSocket connected')
  }

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data)
      handleWebSocketMessage(message)
    } catch (error) {
      console.error('WebSocket message parse error:', error)
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    wsConnected.value = false
  }

  ws.onclose = () => {
    wsConnected.value = false
    console.log('FIO WebSocket disconnected')
  }
}

const handleWebSocketMessage = (message) => {
  const { type, data, stats, host } = message

  if (type === 'joined') {
    console.log('Joined FIO task:', message.task_id)
  } else if (type === 'output') {
    // 实时输出到终端
    if (data) {
      // 尝试从消息中提取主机信息
      let targetHost = host
      if (!targetHost && data.includes('[')) {
        const match = data.match(/\[([^\]]+)\]/)
        if (match) {
          targetHost = match[1]
        }
      }

      // 如果无法确定主机，使用当前激活的标签页
      if (!targetHost && activeHostTab.value) {
        targetHost = activeHostTab.value
      }

      const lines = data.split('\n')
      lines.forEach(line => {
        if (line.trim()) {
          addTerminalLine('info', line, targetHost)
        }
      })
    }
  } else if (type === 'stats') {
    // 更新统计数据 - 支持多主机聚合
    // console.log('📊 Received stats message:', stats, 'from host:', host)
    if (stats && host) {
      // 存储该主机的统计数据
      hostStats.value[host] = {
        iops: stats.iops || 0,
        bw: stats.bw_mb || 0,
        lat: (stats.latency_us / 1000) || 0,  // Convert to ms
        timestamp: Date.now()
      }

      // console.log('📈 Host stats updated:', host, hostStats.value[host])

      // 清除之前的聚合定时器
      if (statsAggregationTimer) {
        clearTimeout(statsAggregationTimer)
      }

      // 延迟 200ms 聚合数据（等待所有主机的数据到达）
      statsAggregationTimer = setTimeout(() => {
        aggregateAndUpdateStats()
      }, 200)
    }
  } else if (type === 'completed') {
    finishTest()
  } else if (type === 'error') {
    addTerminalLine('error', message.error || '未知错误')
  }
}

const joinTask = (taskId) => {
  if (ws && wsConnected.value) {
    ws.send(JSON.stringify({
      action: 'join',
      task_id: taskId
    }))
  }
}

const disconnectWebSocket = () => {
  if (ws) {
    ws.close()
    ws = null
    wsConnected.value = false
  }
}

// Initialize charts
const initCharts = () => {
  const createChart = (ref, key, color) => {
    if (!ref) return null
    return new Chart(ref, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [{
          data: chartData[key],
          borderColor: color,
          backgroundColor: color + '20',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            display: true,
            grid: { display: false }
          },
          y: {
            display: true,
            beginAtZero: true,
            grid: { color: '#f0f0f0' }
          }
        }
      }
    })
  }

  charts.iops = createChart(iopsChart.value, 'iops', '#6B5DD3')
  charts.bw = createChart(bwChart.value, 'bw', '#4CAF50')
  charts.lat = createChart(latChart.value, 'lat', '#ff9800')
}

// 聚合多主机统计数据
const aggregateAndUpdateStats = () => {
  const hosts = Object.keys(hostStats.value)
  if (hosts.length === 0) return

  // console.log('🔄 Aggregating stats from', hosts.length, 'hosts')

  // IOPS 和带宽：多主机相加
  let totalIops = 0
  let totalBw = 0
  let totalLat = 0
  let latCount = 0

  hosts.forEach(host => {
    const stats = hostStats.value[host]
    totalIops += stats.iops
    totalBw += stats.bw
    if (stats.lat > 0) {
      totalLat += stats.lat
      latCount++
    }
  })

  // 延迟：多主机平均值
  const avgLat = latCount > 0 ? totalLat / latCount : 0

  // 更新当前统计数据
  currentStats.iops = totalIops
  currentStats.bw = totalBw
  currentStats.lat = avgLat

  // console.log('📊 Aggregated stats:', {
  //   hosts: hosts.length,
  //   iops: totalIops,
  //   bw: totalBw,
  //   lat: avgLat
  // })

  // 更新图表
  updateCharts()
}

// Update charts
const updateCharts = () => {
  // console.log('🔄 updateCharts called, currentStats:', currentStats)

  // 不再限制数据点数量，显示完整测试时长
  // 移除了 60 个数据点的限制

  chartData.labels.push(elapsedTime.value)
  chartData.iops.push(currentStats.iops)
  chartData.bw.push(currentStats.bw)
  chartData.lat.push(currentStats.lat)

  // console.log('📊 Chart data updated:', {
  //   labels: chartData.labels.length,
  //   iops: chartData.iops[chartData.iops.length - 1],
  //   bw: chartData.bw[chartData.bw.length - 1],
  //   lat: chartData.lat[chartData.lat.length - 1]
  // })

  // console.log('🎨 Charts object:', {
  //   iops: charts.iops ? 'initialized' : 'null',
  //   bw: charts.bw ? 'initialized' : 'null',
  //   lat: charts.lat ? 'initialized' : 'null'
  // })

  // 更新每个图表的数据 - 使用 toRaw 避免响应式循环引用
  if (charts.iops) {
    charts.iops.data.labels = toRaw(chartData.labels)
    charts.iops.data.datasets[0].data = toRaw(chartData.iops)
    charts.iops.update('none')
    // console.log('✅ IOPS chart updated')
  }

  if (charts.bw) {
    charts.bw.data.labels = toRaw(chartData.labels)
    charts.bw.data.datasets[0].data = toRaw(chartData.bw)
    charts.bw.update('none')
    // console.log('✅ BW chart updated')
  }

  if (charts.lat) {
    charts.lat.data.labels = toRaw(chartData.labels)
    charts.lat.data.datasets[0].data = toRaw(chartData.lat)
    charts.lat.update('none')
    // console.log('✅ Latency chart updated')
  }
}

// Update stats
const updateStats = () => {
  if (currentStats.iops > 0) {
    const currentAvgIops = avgIops.value === '--' ? 0 : parseFloat(avgIops.value)
    const count = chartData.iops.length
    avgIops.value = ((currentAvgIops * count + currentStats.iops) / (count + 1)).toFixed(0)
    maxStats.iops = Math.max(maxStats.iops, currentStats.iops)
    minStats.iops = Math.min(minStats.iops, currentStats.iops)
  }

  if (currentStats.bw > 0) {
    const currentAvgBw = avgBw.value === '--' ? 0 : parseFloat(avgBw.value)
    const count = chartData.bw.length
    avgBw.value = ((currentAvgBw * count + currentStats.bw) / (count + 1)).toFixed(1)
    maxStats.bw = Math.max(maxStats.bw, currentStats.bw)
  }

  if (currentStats.lat > 0) {
    const currentAvgLat = avgLat.value === '--' ? 0 : parseFloat(avgLat.value)
    const count = chartData.lat.length
    avgLat.value = ((currentAvgLat * count + currentStats.lat) / (count + 1)).toFixed(2)
  }
}

// Validate hosts
const validateHosts = async () => {
  const validHosts = getValidHosts()
  addTerminalLine('info', `验证 ${validHosts.length} 台主机连接...`)

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
    validationResults.value = data.results

    // Update connected hosts list
    connectedHosts.value = data.results
      .filter(r => r.status === 'success')
      .map(r => r.host)

    // 初始化每个主机的终端
    connectedHosts.value.forEach(host => {
      if (!hostTerminals.value[host]) {
        hostTerminals.value[host] = []
      }
    })

    // 设置第一个主机为激活标签
    if (connectedHosts.value.length > 0 && !activeHostTab.value) {
      activeHostTab.value = connectedHosts.value[0]
    }

    data.results.forEach(r => {
      const icon = r.status === 'success' ? '✅' : r.status === 'warning' ? '⚠️' : '❌'
      addTerminalLine(r.status === 'error' ? 'error' : 'info', `${icon} ${r.host}: ${r.message}`)
    })

    if (data.results.every(r => r.status === 'success')) {
      showNotification('所有主机连接成功', 'success')
    } else {
      showNotification('部分主机连接失败', 'warning')
    }
  } catch (error) {
    addTerminalLine('error', `验证失败: ${error.message}`)
    showNotification(`验证失败: ${error.message}`, 'error')
  }
}

// Start test
const startTest = async () => {
  const validHosts = getValidHosts()

  // Generate FIO command for console output
  let fioCommand = 'fio --direct=1'

  if (params.ioengine === 'rbd') {
    // RBD engine command
    fioCommand += ` --ioengine=rbd --pool=${params.pool || 'pool-rbdtest1'} --rbdname=${params.filename || 'rbdtest1'}`
  } else {
    // libaio engine command
    fioCommand += ` --filename=${params.filename || '/dev/sdb'} --ioengine=libaio`
  }

  fioCommand += ` --iodepth=${params.iodepth} --numjobs=${params.numjobs} --rw=${params.rw} --bs=${params.bs}`
  fioCommand += ` --group_reporting --name=mytest --size=${params.size || '100G'}`
  fioCommand += ` --status-interval=1`  // 每秒输出一次状态

  if (params.runtime) {
    fioCommand += ` --runtime=${params.runtime} --time_based`
  }

  // Add CPU affinity if specified
  if (params.cpus_allowed && params.cpus_allowed.trim()) {
    fioCommand += ` --cpus_allowed=${params.cpus_allowed} --cpus_allowed_policy=split`
  }

  // Reset stats
  currentStats.iops = 0
  currentStats.bw = 0
  currentStats.lat = 0
  avgIops.value = '--'
  avgBw.value = '--'
  avgLat.value = '--'
  maxStats.iops = 0
  maxStats.bw = 0
  elapsedSeconds.value = 0
  chartData.iops = []
  chartData.bw = []
  chartData.lat = []
  chartData.labels = []
  hostStats.value = {} // 清空多主机统计数据

  addTerminalLine('info', '='.repeat(50))
  addTerminalLine('info', `开始 FIO 测试`)
  addTerminalLine('info', `类型: ${rwLabels[params.rw]}, 块大小: ${params.bs}, IO深度: ${params.iodepth}`)
  addTerminalLine('info', `线程: ${params.numjobs}, 时长: ${params.runtime}s, 主机数: ${validHosts.length}`)
  addTerminalLine('info', `命令: ${fioCommand}`)

  try {
    const response = await fetch(`${API_BASE}/start-test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hosts: validHosts,
        username: config.username,
        password: config.password,
        params: {
          rw: params.rw,
          rwmixread: params.rwmixread,
          bs: params.bs,
          iodepth: params.iodepth,
          numjobs: params.numjobs,
          runtime: params.runtime,
          size: params.size,
          ioengine: params.ioengine,
          filename: params.filename,
          pool: params.pool,
          cpus_allowed: params.cpus_allowed
        }
      })
    })

    const data = await response.json()

    if (data.status === 'success') {
      taskId.value = data.task_id
      isTesting.value = true
      testCompleted.value = false

      // 连接 WebSocket 并加入任务
      if (!wsConnected.value) {
        connectWebSocket()
        // 等待连接建立后加入任务
        setTimeout(() => {
          joinTask(taskId.value)
          startElapsedTimer()
        }, 500)
      } else {
        joinTask(taskId.value)
        startElapsedTimer()
      }

      showNotification('测试已启动', 'success')
    } else {
      addTerminalLine('error', `启动失败: ${data.error}`)
      showNotification(`启动失败: ${data.error}`, 'error')
    }
  } catch (error) {
    addTerminalLine('error', `启动失败: ${error.message}`)
    showNotification(`启动失败: ${error.message}`, 'error')
  }
}

// Stop test
const stopTest = async () => {
  if (taskId.value) {
    // 通过 WebSocket 发送停止命令
    if (ws && wsConnected.value) {
      ws.send(JSON.stringify({
        action: 'stop',
        task_id: taskId.value
      }))
    }

    // 也调用 HTTP API 作为备份
    await fetch(`${API_BASE}/stop-test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId.value })
    })
  }

  isTesting.value = false
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }

  addTerminalLine('warning', '测试已手动停止')
  showNotification('测试已停止', 'info')
}

// Elapsed timer
const startElapsedTimer = () => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
  }

  pollTimer.value = setInterval(() => {
    elapsedSeconds.value++
  }, 1000)
}

// Polling (保留作为备用，但不再使用)
const startPolling = () => {
  const elapsedTimer = setInterval(() => {
    elapsedSeconds.value++
  }, 1000)

  pollTimer.value = setInterval(async () => {
    if (!taskId.value) return

    try {
      const response = await fetch(`${API_BASE}/get-output?task_id=${taskId.value}`)
      const data = await response.json()

      if (data.status === 'success') {
        // Update stats
        const stats = data.stats || {}
        currentStats.iops = stats.iops || 0
        currentStats.bw = (stats.bw_mb || 0) / 1024  // Convert to MB/s from GB/s
        currentStats.lat = (stats.latency_us || stats.clat_avg_us || 0) / 1000  // Convert to ms

        updateStats()
        updateCharts()

        // Add output lines
        if (data.output && data.output.length > 0) {
          const lastLines = data.output.slice(-5)
          lastLines.forEach(line => {
            if (line.includes('iops=') || line.includes('bw=')) {
              addTerminalLine('success', line.trim())
            }
          })
        }

        // Check completion
        if (data.status === 'completed' || data.status === 'stopped') {
          finishTest()
        }
      }
    } catch (error) {
      console.error('Polling error:', error)
    }
  }, 500)

  // Store timer references
  pollTimer.value.elapsed = elapsedTimer
}

// Finish test
const finishTest = () => {
  isTesting.value = false
  testCompleted.value = true

  // Clear timers
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }

  // 清理聚合定时器
  if (statsAggregationTimer) {
    clearTimeout(statsAggregationTimer)
    statsAggregationTimer = null
  }

  // 计算平均值（从图表数据中计算）
  if (chartData.iops.length > 0) {
    const sumIops = chartData.iops.reduce((a, b) => a + b, 0)
    avgIops.value = (sumIops / chartData.iops.length).toFixed(0)
  }

  if (chartData.bw.length > 0) {
    const sumBw = chartData.bw.reduce((a, b) => a + b, 0)
    avgBw.value = (sumBw / chartData.bw.length).toFixed(1)
  }

  if (chartData.lat.length > 0) {
    const sumLat = chartData.lat.reduce((a, b) => a + b, 0)
    avgLat.value = (sumLat / chartData.lat.length).toFixed(2)
  }

  // Final stats
  finalStats.iops = parseFloat(avgIops.value) || 0
  finalStats.bw = parseFloat(avgBw.value) || 0
  finalStats.lat = parseFloat(avgLat.value) || 0

  addTerminalLine('success', '='.repeat(50))
  addTerminalLine('success', `测试完成!`)
  addTerminalLine('success', `平均 IOPS: ${avgIops.value}, 平均带宽: ${avgBw.value} MB/s, 平均延迟: ${avgLat.value} ms`)

  showNotification('测试完成', 'success')
}

// Cleanup
onUnmounted(() => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
  }
  Object.values(charts).forEach(chart => {
    if (chart) chart.destroy()
  })
  disconnectWebSocket()
})

// Initialize charts on mount
onMounted(() => {
  nextTick(() => {
    initCharts()
  })
  // 初始化时连接 WebSocket
  connectWebSocket()
})
</script>

<style scoped>
.fio-page {
  min-height: 100vh;
  padding: 20px;
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 50%, #9B8FF8 100%);
  position: relative;
}
.fio-page::before { content: ''; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: repeating-linear-gradient(45deg, transparent, transparent 35px, rgba(255,255,255,0.05) 35px, rgba(255,255,255,0.05) 70px); pointer-events: none; z-index: 0; }
.fio-page > * { position: relative; z-index: 1; }

.main-content {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 12px;
}

.form-row .form-group {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  color: #666;
  font-size: 12px;
  margin-bottom: 4px;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  font-family: monospace;
}

.form-group textarea {
  resize: vertical;
  min-height: 60px;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #6B5DD3;
  box-shadow: 0 0 0 3px rgba(107, 93, 211, 0.1);
}

.hosts-section {
  margin: 15px 0;
}

.hosts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-size: 12px;
  color: #666;
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

.host-list {
  max-height: 150px;
  overflow-y: auto;
}

.host-item {
  display: flex;
  gap: 5px;
  margin-bottom: 5px;
}

.host-item input {
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

.btn-compact {
  padding: 6px 12px !important;
  font-size: 12px !important;
  width: auto !important;
}

.btn-full {
  width: 100%;
}

.btn-large {
  padding: 15px;
  font-size: 16px;
}

.validation-summary {
  margin-top: 10px;
  text-align: center;
}

.badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
}

.badge.success {
  background: #e8f5e9;
  color: #4CAF50;
}

.badge.warning {
  background: #fff3e0;
  color: #ff9800;
}

.badge.error {
  background: #ffebee;
  color: #f44336;
}

.test-type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.radio-card {
  padding: 10px 5px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  text-align: center;
  transition: all 0.3s;
}

.radio-card:hover {
  border-color: #6B5DD3;
}

.radio-card.active {
  border-color: #6B5DD3;
  background: rgba(107, 93, 211, 0.1);
}

.radio-card input {
  display: none;
}

.radio-icon {
  font-size: 24px;
  display: block;
  margin-bottom: 5px;
}

.radio-name {
  font-size: 12px;
  color: #333;
}

.mix-slider {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mix-slider input {
  flex: 1;
}

.mix-label {
  font-size: 13px;
  color: #666;
  min-width: 80px;
}

.params-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.actions-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.top-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.summary-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 15px;
}

.card-icon {
  font-size: 20px;
}

.card-content {
  flex: 1;
}

.card-label {
  font-size: 13px;
  color: #999;
  margin-bottom: 5px;
}

.card-value {
  font-size: 16px;
  line-height: 1.6;
  font-weight: bold;
  color: #6B5DD3;
}

.card-unit {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}

.middle-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.chart-wrapper {
  background: white;
  padding: 15px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.chart-wrapper h3 {
  font-size: 14px;
  color: #333;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 2px solid #f0f0f0;
}

.chart-wrapper canvas {
  max-height: 200px !important;
  height: 200px !important;
}

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

.terminal-icon {
  font-size: 20px;
}

.terminal-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.terminal-controls {
  display: flex;
  align-items: center;
  gap: 10px;
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

.connected-hosts {
  margin-bottom: 15px;
}

.connected-hosts-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.host-badge {
  display: inline-block;
  padding: 4px 12px;
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 100%);
  color: white;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.progress-container {
  margin-bottom: 15px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 5px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6B5DD3 0%, #8B7FE8 50%, #9B8FF8 100%);
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-text {
  font-size: 12px;
  color: #666;
  text-align: center;
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

@media (max-width: 1200px) {
  .main-content {
    grid-template-columns: 1fr;
  }

  .charts-section {
    grid-template-columns: 1fr;
  }

  .results-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
