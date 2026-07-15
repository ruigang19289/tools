<template>
  <div class="fio-page">
    <PageHeader
      icon="📊"
      title="FIO 性能测试"
    />

    <div class="main-content">
      <div class="left-panel">
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
              <input type="number" v-model="config.port" placeholder="22">
            </div>
          </div>

          <div class="form-group">
            <label>密码:</label>
            <input type="text" v-model="config.password" placeholder="******">
          </div>

          <button class="btn btn-primary btn-full" @click="validateHosts" :disabled="!canValidate">
            验证连接
          </button>

          <div v-if="validationResults.length > 0" class="validation-summary">
            <span class="badge success" v-if="validationResults.every(r => r.status === 'success' && r.has_fio)">
              ✅ 全部连接成功
            </span>
            <span class="badge warning" v-else-if="validationResults.some(r => r.status === 'success' || r.status === 'warning')">
              ⚠️ 部分可用 ({{ validationResults.filter(r => r.status === 'success' && r.has_fio).length }}/{{ getValidHosts().length }})
            </span>
            <span class="badge error" v-else>
              ❌ 连接失败
            </span>
          </div>
        </div>

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

        <div class="section">
          <h2 class="section-title">测试参数</h2>

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

          <template v-else>
            <div class="form-row">
              <div class="form-group">
                <label>卷名称:</label>
                <input type="text" v-model="params.filename" placeholder="/dev/sdb">
              </div>
              <div class="form-group"></div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>测试大小:</label>
                <input type="text" v-model="params.size" placeholder="100G">
              </div>
              <div class="form-group"></div>
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

        <div class="section actions-section">
          <button class="btn btn-primary btn-full" @click="startTest" :disabled="!canStart || isTesting">
            {{ isTesting ? '测试中...' : '开始测试' }}
          </button>

          <button v-if="isTesting" class="btn btn-danger btn-full" @click="stopTest">
            停止测试
          </button>
        </div>
      </div>

      <div class="right-panel">
        <div class="top-row">
          <div class="summary-cards">
            <div class="card">
              <div class="card-icon">⚡</div>
              <div class="card-content">
                <div class="card-label">平均 I/O 速率</div>
                <div class="card-value">{{ avgIops }}</div>
                <div v-if="mixStatsMode" class="card-subvalue">读 {{ avgReadIops }} / 写 {{ avgWriteIops }}</div>
                <div v-else class="card-subvalue card-subvalue-placeholder">&nbsp;</div>
                <div class="card-unit">IOPS</div>
              </div>
            </div>
            <div class="card">
              <div class="card-icon">⏱️</div>
              <div class="card-content">
                <div class="card-label">响应时间</div>
                <div class="card-value">{{ avgLat }}</div>
                <div class="card-subvalue card-subvalue-placeholder">&nbsp;</div>
                <div class="card-unit">ms</div>
              </div>
            </div>
            <div class="card">
              <div class="card-icon">📈</div>
              <div class="card-content">
                <div class="card-label">吞吐量</div>
                <div class="card-value">{{ avgBw }}</div>
                <div v-if="mixStatsMode" class="card-subvalue">读 {{ avgReadBw }} / 写 {{ avgWriteBw }}</div>
                <div v-else class="card-subvalue card-subvalue-placeholder">&nbsp;</div>
                <div class="card-unit">MB/s</div>
              </div>
            </div>
            <div class="card card-empty">
              <div class="card-icon">⏰</div>
              <div class="card-content">
                <div class="card-label">运行时长</div>
                <div class="card-value">{{ elapsedTime }}</div>
                <div class="card-subvalue card-subvalue-placeholder">&nbsp;</div>
                <div class="card-unit"></div>
              </div>
            </div>
          </div>

          <div class="chart-wrapper">
            <h3>吞吐量 (MB/s)</h3>
            <canvas ref="bwChart"></canvas>
          </div>
        </div>

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

          <div v-if="isTesting" class="progress-container">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <div class="progress-text">{{ elapsedTime }} / {{ params.runtime }}s ({{ progressPercent.toFixed(0) }}%)</div>
          </div>

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

let ws = null
const wsConnected = ref(false)
let wsConnectPromise = null
let pendingJoinTaskId = null

const hostsText = ref('')

const config = reactive({
  username: 'root',
  password: '',
  port: 22
})

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

const rwLabels = {
  randread: '随机读',
  randwrite: '随机写',
  randrw: '混合读写',
  read: '顺序读',
  write: '顺序写'
}

const isTesting = ref(false)
const testCompleted = ref(false)
const taskId = ref('')
const pollTimer = ref(null)
const elapsedSeconds = ref(0)

const currentStats = reactive({ iops: 0, bw: 0, lat: 0, readIops: 0, writeIops: 0, readBw: 0, writeBw: 0 })
const avgIops = ref('--')
const avgBw = ref('--')
const avgLat = ref('--')
const avgReadIops = ref('--')
const avgWriteIops = ref('--')
const avgReadBw = ref('--')
const avgWriteBw = ref('--')
const mixStatsMode = computed(() => params.rw === 'randrw')
const maxStats = reactive({ iops: 0, bw: 0, lat: 0 })
const minStats = reactive({ iops: 999999999, bw: 999999999, lat: 999999999 })
const finalStats = reactive({ iops: 0, bw: 0, lat: 0 })

const hostStats = ref({})
let statsAggregationTimer = null

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

const terminalLines = ref([])
const terminalWindow = ref(null)
const hostTerminals = ref({})
const activeHostTab = ref('')

const validationResults = ref([])
const connectedHosts = ref([])

const notification = reactive({
  show: false,
  message: '',
  type: 'info'
})

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

const canValidate = computed(() => {
  const validHosts = getValidHosts()
  return validHosts.length > 0 && config.username && config.password
})

const canStart = computed(() => {
  const validHosts = getValidHosts()
  return validHosts.length > 0 && validationResults.value.length > 0 &&
    validationResults.value.every(r => r.status === 'success' && r.has_fio)
})

const elapsedTime = computed(() => {
  const mins = Math.floor(elapsedSeconds.value / 60)
  const secs = elapsedSeconds.value % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
})

const progressPercent = computed(() => {
  return Math.min(100, (elapsedSeconds.value / params.runtime) * 100)
})

const getValidHosts = () => {
  return hostsText.value
    .split('\n')
    .map(h => h.trim())
    .filter(h => h)
}

const showNotification = (message, type = 'info') => {
  notification.message = message
  notification.type = type
  notification.show = true
  setTimeout(() => {
    notification.show = false
  }, 3000)
}

const addTerminalLine = (type, text, host = null) => {
  if (host && hostTerminals.value[host]) {
    hostTerminals.value[host].push({ type, text })
  } else {
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

const getCurrentTerminalLines = () => {
  if (activeHostTab.value && hostTerminals.value[activeHostTab.value]) {
    return hostTerminals.value[activeHostTab.value]
  }
  return terminalLines.value
}

const connectWebSocket = () => {
  if (ws && wsConnected.value) {
    return Promise.resolve()
  }

  if (wsConnectPromise) {
    return wsConnectPromise
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/v1/perf/fio/ws`

  wsConnectPromise = new Promise((resolve, reject) => {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      wsConnected.value = true
      if (pendingJoinTaskId) {
        joinTask(pendingJoinTaskId)
        pendingJoinTaskId = null
      }
      resolve()
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
      wsConnected.value = false
      wsConnectPromise = null
      reject(new Error('WebSocket 连接失败'))
    }

    ws.onclose = () => {
      wsConnected.value = false
      wsConnectPromise = null
    }
  })

  return wsConnectPromise
}

const handleWebSocketMessage = (message) => {
  const { type, data, stats, host } = message

  if (type === 'joined') {
    return
  } else if (type === 'output') {
    if (data) {
      let targetHost = host
      if (!targetHost && data.includes('[')) {
        const match = data.match(/\[([^\]]+)\]/)
        if (match) {
          targetHost = match[1]
        }
      }

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
    if (stats && host) {
      hostStats.value[host] = {
        iops: stats.iops || 0,
        bw: stats.bw_mb || 0,
        lat: (stats.latency_us / 1000) || 0,
        readIops: stats.read_iops || 0,
        writeIops: stats.write_iops || 0,
        readBw: stats.read_bw_mb || 0,
        writeBw: stats.write_bw_mb || 0,
        timestamp: Date.now()
      }

      if (statsAggregationTimer) {
        clearTimeout(statsAggregationTimer)
      }

      statsAggregationTimer = setTimeout(() => {
        aggregateAndUpdateStats()
      }, 200)
    }
  } else if (type === 'completed') {
    finishTest(message.status || 'completed')
  } else if (type === 'error') {
    addTerminalLine('error', message.error || '未知错误', host)
    finishTest('error')
  }
}

const joinTask = (taskId) => {
  if (ws && wsConnected.value) {
    ws.send(JSON.stringify({
      action: 'join',
      task_id: taskId
    }))
    return true
  }

  pendingJoinTaskId = taskId
  return false
}

const disconnectWebSocket = () => {
  pendingJoinTaskId = null
  wsConnectPromise = null
  if (ws) {
    ws.close()
    ws = null
    wsConnected.value = false
  }
}

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
          x: { display: true, grid: { display: false } },
          y: { display: true, beginAtZero: true, grid: { color: '#f0f0f0' } }
        }
      }
    })
  }

  charts.iops = createChart(iopsChart.value, 'iops', '#6B5DD3')
  charts.bw = createChart(bwChart.value, 'bw', '#4CAF50')
  charts.lat = createChart(latChart.value, 'lat', '#ff9800')
}

const aggregateAndUpdateStats = () => {
  const hosts = Object.keys(hostStats.value)
  if (hosts.length === 0) return

  let totalIops = 0
  let totalBw = 0
  let totalLat = 0
  let totalReadIops = 0
  let totalWriteIops = 0
  let totalReadBw = 0
  let totalWriteBw = 0
  let latCount = 0

  hosts.forEach(host => {
    const stats = hostStats.value[host]
    totalIops += stats.iops
    totalBw += stats.bw
    totalReadIops += stats.readIops || 0
    totalWriteIops += stats.writeIops || 0
    totalReadBw += stats.readBw || 0
    totalWriteBw += stats.writeBw || 0
    if (stats.lat > 0) {
      totalLat += stats.lat
      latCount++
    }
  })

  currentStats.readIops = totalReadIops
  currentStats.writeIops = totalWriteIops
  currentStats.readBw = totalReadBw
  currentStats.writeBw = totalWriteBw

  const avgLatency = latCount > 0 ? totalLat / latCount : 0

  currentStats.iops = totalIops
  currentStats.bw = totalBw
  currentStats.lat = avgLatency

  updateCharts()
}

const updateCharts = () => {
  chartData.labels.push(elapsedTime.value)
  chartData.iops.push(currentStats.iops)
  chartData.bw.push(currentStats.bw)
  chartData.lat.push(currentStats.lat)

  if (charts.iops) {
    charts.iops.data.labels = toRaw(chartData.labels)
    charts.iops.data.datasets[0].data = toRaw(chartData.iops)
    charts.iops.update('none')
  }

  if (charts.bw) {
    charts.bw.data.labels = toRaw(chartData.labels)
    charts.bw.data.datasets[0].data = toRaw(chartData.bw)
    charts.bw.update('none')
  }

  if (charts.lat) {
    charts.lat.data.labels = toRaw(chartData.labels)
    charts.lat.data.datasets[0].data = toRaw(chartData.lat)
    charts.lat.update('none')
  }
}

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
        password: config.password,
        port: config.port
      })
    })

    const data = await response.json()
    validationResults.value = data.results

    connectedHosts.value = data.results
      .filter(r => r.status === 'success' || r.status === 'warning')
      .map(r => r.host)

    connectedHosts.value.forEach(host => {
      if (!hostTerminals.value[host]) {
        hostTerminals.value[host] = []
      }
    })

    if (connectedHosts.value.length > 0 && !activeHostTab.value) {
      activeHostTab.value = connectedHosts.value[0]
    }

    data.results.forEach(r => {
      const icon = r.status === 'success' ? '✅' : r.status === 'warning' ? '⚠️' : '❌'
      addTerminalLine(r.status === 'error' ? 'error' : 'info', `${icon} ${r.host}: ${r.message}`)
    })

    const hasError = data.results.some(r => r.status === 'error')
    const hasWarning = data.results.some(r => r.status === 'warning')

    if (data.results.every(r => r.status === 'success')) {
      showNotification('所有主机连接成功', 'success')
    } else if (hasError && hasWarning) {
      showNotification('部分主机连接失败，部分主机未安装 FIO', 'warning')
    } else if (hasError) {
      showNotification('部分主机连接失败', 'warning')
    } else if (hasWarning) {
      showNotification('部分主机未安装 FIO', 'warning')
    }
  } catch (error) {
    addTerminalLine('error', `验证失败: ${error.message}`)
    showNotification(`验证失败: ${error.message}`, 'error')
  }
}

const startTest = async () => {
  const validHosts = getValidHosts()

  let fioCommand = 'fio --direct=1'

  if (params.ioengine === 'rbd') {
    fioCommand += ` --ioengine=rbd --pool=${params.pool || 'pool-rbdtest1'} --rbdname=${params.filename || 'rbdtest1'}`
  } else {
    fioCommand += ` --filename=${params.filename || '/dev/sdb'} --ioengine=libaio`
  }

  fioCommand += ` --iodepth=${params.iodepth} --numjobs=${params.numjobs} --rw=${params.rw} --bs=${params.bs}`
  if (params.rw === 'randrw') {
    fioCommand += ` --rwmixread=${params.rwmixread}`
  }
  fioCommand += ` --group_reporting --name=mytest --size=${params.size || '100G'}`
  fioCommand += ' --status-interval=1'

  if (params.runtime) {
    fioCommand += ` --runtime=${params.runtime} --time_based`
  }

  if (params.cpus_allowed && params.cpus_allowed.trim()) {
    fioCommand += ` --cpus_allowed=${params.cpus_allowed} --cpus_allowed_policy=split`
  }

  currentStats.iops = 0
  currentStats.bw = 0
  currentStats.lat = 0
  currentStats.readIops = 0
  currentStats.writeIops = 0
  currentStats.readBw = 0
  currentStats.writeBw = 0
  avgIops.value = '--'
  avgBw.value = '--'
  avgLat.value = '--'
  avgReadIops.value = '--'
  avgWriteIops.value = '--'
  avgReadBw.value = '--'
  avgWriteBw.value = '--'
  maxStats.iops = 0
  maxStats.bw = 0
  elapsedSeconds.value = 0
  chartData.iops = []
  chartData.bw = []
  chartData.lat = []
  chartData.labels = []
  hostStats.value = {}

  addTerminalLine('info', '='.repeat(50))
  addTerminalLine('info', '开始 FIO 测试')
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
        port: config.port,
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

      await connectWebSocket()
      joinTask(taskId.value)
      startElapsedTimer()

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

const stopTest = async () => {
  if (taskId.value) {
    if (ws && wsConnected.value) {
      ws.send(JSON.stringify({ action: 'stop', task_id: taskId.value }))
    }

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

const startElapsedTimer = () => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
  }

  pollTimer.value = setInterval(() => {
    elapsedSeconds.value++
  }, 1000)
}

const finishTest = (status = 'completed') => {
  isTesting.value = false
  testCompleted.value = status === 'completed' || status === 'partial'

  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }

  if (statsAggregationTimer) {
    clearTimeout(statsAggregationTimer)
    statsAggregationTimer = null
  }

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

  if (mixStatsMode.value) {
    avgReadIops.value = currentStats.readIops.toFixed(0)
    avgWriteIops.value = currentStats.writeIops.toFixed(0)
    avgReadBw.value = currentStats.readBw.toFixed(1)
    avgWriteBw.value = currentStats.writeBw.toFixed(1)
  }

  finalStats.iops = parseFloat(avgIops.value) || 0
  finalStats.bw = parseFloat(avgBw.value) || 0
  finalStats.lat = parseFloat(avgLat.value) || 0

  const statusText = status === 'partial' ? '测试部分完成' : status === 'stopped' ? '测试已停止' : status === 'error' ? '测试失败' : '测试完成'
  const lineType = status === 'error' ? 'error' : status === 'stopped' ? 'warning' : 'success'
  const notificationType = status === 'error' ? 'error' : status === 'stopped' ? 'info' : status === 'partial' ? 'warning' : 'success'

  addTerminalLine(lineType, '='.repeat(50))
  addTerminalLine(lineType, `${statusText}!`)
  addTerminalLine(lineType, `平均 IOPS: ${avgIops.value}, 平均带宽: ${avgBw.value} MB/s, 平均延迟: ${avgLat.value} ms`)
  if (mixStatsMode.value) {
    addTerminalLine(lineType, `混合读写拆分: 读 IOPS ${avgReadIops.value}, 写 IOPS ${avgWriteIops.value}, 读带宽 ${avgReadBw.value} MB/s, 写带宽 ${avgWriteBw.value} MB/s`)
  }

  showNotification(statusText, notificationType)
}

onUnmounted(() => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
  }
  Object.values(charts).forEach(chart => {
    if (chart) chart.destroy()
  })
  disconnectWebSocket()
})

onMounted(() => {
  nextTick(() => {
    initCharts()
    Object.values(charts).forEach(chart => {
      if (chart) chart.update('none')
    })
  })
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

.form-group { margin-bottom: 15px; }
.form-group label { display: block; font-size: 13px; color: #666; margin-bottom: 8px; }
.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.3s;
}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus { outline: none; border-color: #6B5DD3; box-shadow: 0 0 0 3px rgba(107, 93, 211, 0.1); }
.form-group textarea { resize: vertical; min-height: 70px; font-family: inherit; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.btn-full { width: 100%; }
.validation-summary { margin-top: 10px; text-align: center; }
.badge { padding: 4px 12px; border-radius: 20px; font-size: 13px; }
.badge.success { background: #e8f5e9; color: #4CAF50; }
.badge.warning { background: #fff3e0; color: #ff9800; }
.badge.error { background: #ffebee; color: #f44336; }
.test-type-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.radio-card { padding: 10px 5px; border: 2px solid #e0e0e0; border-radius: 8px; cursor: pointer; text-align: center; transition: all 0.3s; }
.radio-card:hover { border-color: #6B5DD3; }
.radio-card.active { border-color: #6B5DD3; background: rgba(107, 93, 211, 0.1); }
.radio-card input { display: none; }
.radio-icon { font-size: 24px; display: block; margin-bottom: 5px; }
.radio-name { font-size: 12px; color: #333; }
.mix-slider { display: flex; align-items: center; gap: 10px; }
.mix-slider input { flex: 1; }
.mix-label { font-size: 13px; color: #666; min-width: 80px; }
.params-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.actions-section { display: flex; flex-direction: column; gap: 10px; }
.right-panel { display: flex; flex-direction: column; gap: 15px; }
.top-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.summary-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); display: flex; align-items: center; gap: 15px; }
.card-icon { font-size: 20px; }
.card-content { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.card-label { font-size: 13px; color: #999; margin-bottom: 5px; }
.card-value { font-size: 16px; line-height: 1.6; font-weight: bold; color: #6B5DD3; }
.card-subvalue { margin-top: 4px; font-size: 12px; color: #666; line-height: 1.4; min-height: 17px; }
.card-subvalue-placeholder { visibility: hidden; }
.card-unit { font-size: 12px; color: #999; margin-top: 2px; }
.middle-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.chart-wrapper { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
.chart-wrapper h3 { font-size: 14px; color: #333; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 2px solid #f0f0f0; }
.chart-wrapper canvas { max-height: 200px !important; height: 200px !important; }
.card-empty .card-unit { visibility: hidden; }
.terminal-section { background: rgba(255, 255, 255, 0.95); border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); display: flex; flex-direction: column; }
.terminal-header { display: flex; justify-content: space-between; align-items: flex-start; margin: 0; margin-bottom: 15px; flex-shrink: 0; }
.terminal-title { font-size: 16px; font-weight: 600; color: #333; }
.terminal-controls { display: flex; gap: 10px; }
.progress-container { margin-bottom: 15px; }
.progress-bar { height: 6px; background: #e0e0e0; border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #6B5DD3, #8B7FE8); transition: width 1s linear; }
.progress-text { margin-top: 5px; font-size: 12px; color: #666; text-align: center; }
.host-tabs { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.host-tab { padding: 6px 12px; background: #f0f0f0; border-radius: 20px; font-size: 12px; cursor: pointer; transition: all 0.3s; }
.host-tab.active { background: #6B5DD3; color: white; }
.terminal-window { background: #1a1a1a; color: #00ff00; font-family: 'Courier New', monospace; font-size: 12px; padding: 15px; border-radius: 8px; height: 300px; overflow-y: auto; white-space: pre-wrap; line-height: 1.5; }
.terminal-empty { color: #666; text-align: center; padding: 40px; }
.terminal-line.error { color: #ff6b6b; }
.terminal-line.success { color: #51cf66; }
.notification { position: fixed; bottom: 20px; right: 20px; padding: 12px 20px; border-radius: 8px; color: white; font-size: 14px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2); z-index: 9999; animation: slideIn 0.3s ease; }
.notification.success { background: #4CAF50; }
.notification.error { background: #f44336; }
.notification.info { background: #2196F3; }
.notification.warning { background: #ff9800; }
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
@media (max-width: 768px) {
  .main-content, .top-row, .middle-row { grid-template-columns: 1fr; }
  .form-row, .params-grid, .summary-cards { grid-template-columns: 1fr; }
  .test-type-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
