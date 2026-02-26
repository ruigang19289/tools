<template>
  <div class="container">
    <!-- 头部 -->
    <header class="header">
      <div style="display: flex; align-items: center; gap: 15px;">
        <router-link to="/" class="back-btn">🏠</router-link>
        <h1>VDBench 可视化</h1>
      </div>
      <div class="header-controls">
        <div class="control-group">
          <label for="testDirSelect">测试目录:</label>
          <select id="testDirSelect" v-model="selectedDir" @change="onDirChange" class="test-dir-select">
            <option value="">选择测试目录</option>
            <option v-for="dir in directories" :key="dir.path" :value="dir.path">
              {{ dir.name }}{{ dir.has_summary ? '' : ' (无summary.html)' }}
            </option>
          </select>
        </div>
        <div class="control-group">
          <label>
            <input type="checkbox" v-model="autoRefresh" @change="toggleAutoRefresh">
            自动刷新
          </label>
        </div>
        <button @click="refresh" class="btn btn-compact">刷新</button>
        <div class="status-indicator">
          <span :class="['status-dot', statusClass]"></span>
          <span id="statusText">{{ statusText }}</span>
        </div>
      </div>
    </header>

    <!-- 汇总信息卡片 -->
    <div class="summary-cards">
      <div class="card">
        <div class="card-icon">⚡</div>
        <div class="card-content">
          <div class="card-label">平均 I/O 速率</div>
          <div class="card-value" id="avgIoRate" v-html="avgIoRate"></div>
          <div class="card-unit" id="avgIoRateUnit">IOPS</div>
        </div>
      </div>
      <div class="card">
        <div class="card-icon">📈</div>
        <div class="card-content">
          <div class="card-label">平均吞吐量</div>
          <div class="card-value" id="avgThroughput" v-html="avgThroughput"></div>
          <div class="card-unit" id="avgThroughputUnit">MB/s</div>
        </div>
      </div>
      <div class="card">
        <div class="card-icon">⏱️</div>
        <div class="card-content">
          <div class="card-label">平均响应时间</div>
          <div class="card-value" id="avgRespTime" v-html="avgRespTime"></div>
          <div class="card-unit" id="avgRespTimeUnit">ms</div>
        </div>
      </div>
      <div class="card">
        <div class="card-icon">💻</div>
        <div class="card-content">
          <div class="card-label">平均 CPU 使用率</div>
          <div class="card-value" id="avgCpu" v-html="avgCpu"></div>
          <div class="card-unit" id="avgCpuUnit">%</div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div id="chartsContainer" class="charts-container columns-2">
      <div class="chart-wrapper">
        <h3>I/O 速率 (IOPS)</h3>
        <canvas ref="ioRateChart"></canvas>
      </div>
      <div class="chart-wrapper">
        <h3>吞吐量 (MB/s)</h3>
        <canvas ref="throughputChart"></canvas>
      </div>
      <div class="chart-wrapper">
        <h3>响应时间 (ms)</h3>
        <canvas ref="respTimeChart"></canvas>
      </div>
      <div class="chart-wrapper">
        <h3>CPU 使用率 (%)</h3>
        <canvas ref="cpuChart"></canvas>
      </div>
      <div class="chart-wrapper">
        <h3>队列深度</h3>
        <canvas ref="queueDepthChart"></canvas>
      </div>
      <div class="chart-wrapper">
        <h3>响应时间标准差</h3>
        <canvas ref="respStddevChart"></canvas>
      </div>
    </div>

    <!-- 元数据信息 -->
    <div class="metadata-section">
      <h3>测试信息</h3>
      <div id="metadataContent" class="metadata-content">
        <p><strong>创建时间:</strong> {{ metadata.created_time || 'N/A' }}</p>
        <p><strong>运行定义:</strong> {{ metadata.run_definitions ? metadata.run_definitions.join(', ') : 'N/A' }}</p>
        <p><strong>最后更新:</strong> {{ lastUpdate }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'
import api from '@/api'

Chart.register(...registerables)

// 响应式数据
const selectedDir = ref('')
const autoRefresh = ref(true)
const statusText = ref('连接中...')
const statusClass = ref('')
const lastUpdate = ref('')

// 汇总数据
const avgIoRate = ref('--')
const avgThroughput = ref('--')
const avgRespTime = ref('--')
const avgCpu = ref('--')

// 元数据
const metadata = ref({
  created_time: '',
  run_definitions: []
})

// 目录列表
const directories = ref([])

// 图表引用
const ioRateChart = ref(null)
const throughputChart = ref(null)
const respTimeChart = ref(null)
const cpuChart = ref(null)
const queueDepthChart = ref(null)
const respStddevChart = ref(null)

// 图表实例
let charts = {}

// 定时器
let autoRefreshTimer = null

// 初始化图表
const initCharts = () => {
  const chartConfigs = [
    { ref: ioRateChart, id: 'ioRateChart', label: 'I/O 速率', color: '#667eea', unit: 'IOPS' },
    { ref: throughputChart, id: 'throughputChart', label: '吞吐量', color: '#f093fb', unit: 'MB/s' },
    { ref: respTimeChart, id: 'respTimeChart', label: '响应时间', color: '#4facfe', unit: 'ms' },
    { ref: cpuChart, id: 'cpuChart', label: 'CPU 使用率', color: '#43e97b', unit: '%' },
    { ref: queueDepthChart, id: 'queueDepthChart', label: '队列深度', color: '#fa709a', unit: '' },
    { ref: respStddevChart, id: 'respStddevChart', label: '响应时间标准差', color: '#feca57', unit: 'ms' }
  ]

  chartConfigs.forEach(config => {
    if (config.ref.value) {
      charts[config.id] = new Chart(config.ref.value, {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: config.label,
            data: [],
            borderColor: config.color,
            backgroundColor: config.color + '20',
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: {
            legend: { display: false },
            tooltip: {
              mode: 'index',
              intersect: false,
              callbacks: {
                label: (context) => `${config.label}: ${context.parsed.y.toFixed(2)} ${config.unit}`
              }
            }
          },
          scales: {
            x: {
              display: true,
              grid: { display: false },
              ticks: { maxTicksLimit: 10 }
            },
            y: {
              display: true,
              beginAtZero: true,
              grid: { color: '#f0f0f0' }
            }
          },
          interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
          }
        }
      })
    }
  })
}

// 更新图表
const updateChart = (chartId, labels, data) => {
  if (charts[chartId]) {
    charts[chartId].data.labels = labels
    charts[chartId].data.datasets[0].data = data
    charts[chartId].update('none')
  }
}

// 更新汇总卡片
const updateSummaryCards = (summary) => {
  if (summary.by_run_definition && Object.keys(summary.by_run_definition).length > 0) {
    updateGroupedSummaryCards(summary.by_run_definition)
  } else {
    avgIoRate.value = summary.io_rate?.avg?.toFixed(2) || '--'
    avgThroughput.value = summary.throughput_mb?.avg?.toFixed(2) || '--'
    avgRespTime.value = summary.response_time_ms?.avg?.toFixed(2) || '--'
    avgCpu.value = summary.cpu_usage_pct?.avg?.toFixed(2) || '--'
  }
}

// 更新分组汇总卡片
const updateGroupedSummaryCards = (byRunDefinition) => {
  const sortedRds = Object.keys(byRunDefinition).sort()
  const units = ['avgIoRateUnit', 'avgThroughputUnit', 'avgRespTimeUnit', 'avgCpuUnit']
  units.forEach(unitId => {
    const el = document.getElementById(unitId)
    if (el) el.style.display = 'none'
  })

  avgIoRate.value = sortedRds.map(rd => {
    const data = byRunDefinition[rd]
    return `<div class="stat-row"><span class="stat-label">${rd}-${data.test_type}:</span> <span class="stat-value">${data.io_rate.avg.toFixed(2)} IOPS</span></div>`
  }).join('')

  avgThroughput.value = sortedRds.map(rd => {
    const data = byRunDefinition[rd]
    return `<div class="stat-row"><span class="stat-label">${rd}-${data.test_type}:</span> <span class="stat-value">${data.throughput_mb.avg.toFixed(2)} MB/s</span></div>`
  }).join('')

  avgRespTime.value = sortedRds.map(rd => {
    const data = byRunDefinition[rd]
    return `<div class="stat-row"><span class="stat-label">${rd}-${data.test_type}:</span> <span class="stat-value">${data.response_time_ms.avg.toFixed(2)} ms</span></div>`
  }).join('')

  avgCpu.value = sortedRds.map(rd => {
    const data = byRunDefinition[rd]
    return `<div class="stat-row"><span class="stat-label">${rd}-${data.test_type}:</span> <span class="stat-value">${data.cpu_usage_pct.avg.toFixed(2)}%</span></div>`
  }).join('')
}

// 更新状态
const updateStatus = (status, text) => {
  statusText.value = text
  statusClass.value = ''
  if (status === 'connected') {
    statusClass.value = 'connected'
  } else if (status === 'error') {
    statusClass.value = 'error'
  }
}

// 加载数据
const loadData = async (testName) => {
  if (!testName) {
    return
  }

  updateStatus('loading', '加载中...')

  try {
    const summaryRes = await api.get(`/perf/vdbench/summary/?name=${testName}`)
    const dataRes = await api.get(`/perf/vdbench/data/?name=${testName}`)

    updateSummaryCards(summaryRes.summary || summaryRes)
    updateChartsData(dataRes.performance_data || dataRes)
    metadata.value.created_time = summaryRes.metadata?.created_time || ''
    metadata.value.run_definitions = summaryRes.metadata?.run_definitions || []
    lastUpdate.value = new Date().toLocaleString('zh-CN')

    updateStatus('connected', '已连接')
  } catch (error) {
    console.error('加载数据失败:', error)
    updateStatus('error', '连接失败')
  }
}

// 更新图表数据
const updateChartsData = (performanceData) => {
  if (!performanceData || performanceData.length === 0) {
    return
  }

  const labels = performanceData.map(d => `${d.interval}`)

  updateChart('ioRateChart', labels, performanceData.map(d => d.io_rate))
  updateChart('throughputChart', labels, performanceData.map(d => d.mb_sec))
  updateChart('respTimeChart', labels, performanceData.map(d => d.resp_time))
  updateChart('cpuChart', labels, performanceData.map(d => d.cpu_total))
  updateChart('queueDepthChart', labels, performanceData.map(d => d.queue_depth))
  updateChart('respStddevChart', labels, performanceData.map(d => d.resp_stddev))
}

// 加载测试目录列表
const loadTestDirectories = async () => {
  try {
    const data = await api.get('/perf/vdbench/list/')

    directories.value = data.directories || []

    if (directories.value.length === 0) {
      updateStatus('error', 'vdbench-result目录为空')
      return
    }

    // 自动选择第一个有效的目录
    const firstValid = directories.value.find(dir => dir.has_summary)
    if (firstValid) {
      selectedDir.value = firstValid.path
      await loadTestDirectory(firstValid.path)
    } else {
      updateStatus('error', '没有可用的测试数据')
    }
  } catch (error) {
    console.error('加载测试目录列表失败:', error)
    updateStatus('error', '加载目录失败')
  }
}

// 加载指定测试目录
const loadTestDirectory = async (dirPath) => {
  if (!dirPath) return

  updateStatus('loading', '加载测试数据中...')

  try {
    await api.post('/perf/vdbench/load/', { name: dirPath.split('/').pop() })
    const testName = dirPath.split('/').pop()
    await loadData(testName)
    updateStatus('connected', '已加载')
  } catch (error) {
    updateStatus('error', error.message || '加载失败')
  }
}

// 目录选择变化
const onDirChange = async () => {
  if (selectedDir.value) {
    const selectedDirInfo = directories.value.find(d => d.path === selectedDir.value)
    if (selectedDirInfo && !selectedDirInfo.has_summary) {
      clearChartsAndSummary()
      updateStatus('error', '没有找到summary.html')
      return
    }
    await loadTestDirectory(selectedDir.value)
  }
}

// 刷新
const refresh = async () => {
  // 重新加载目录列表
  await loadTestDirectories()
}

// 清空图表和汇总数据
const clearChartsAndSummary = () => {
  // 清空汇总数据
  avgIoRate.value = '--'
  avgThroughput.value = '--'
  avgRespTime.value = '--'
  avgCpu.value = '--'

  // 清空元数据
  metadata.value = {
    created_time: '',
    run_definitions: []
  }

  // 清空所有图表
  Object.keys(charts).forEach(chartId => {
    if (charts[chartId]) {
      charts[chartId].data.labels = []
      charts[chartId].data.datasets[0].data = []
      charts[chartId].update()
    }
  })
}

// 自动刷新开关
const toggleAutoRefresh = () => {
  if (autoRefresh.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

// 启动自动刷新
const startAutoRefresh = () => {
  stopAutoRefresh()
  autoRefreshTimer = setInterval(() => {
    if (selectedDir.value) {
      loadData(selectedDir.value.split('/').pop())
    }
  }, 30000)
}

// 停止自动刷新
const stopAutoRefresh = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

// 生命周期
onMounted(async () => {
  await nextTick()
  initCharts()
  await loadTestDirectories()
  if (autoRefresh.value) {
    startAutoRefresh()
  }
})

onUnmounted(() => {
  stopAutoRefresh()
  Object.values(charts).forEach(chart => chart.destroy())
})
</script>

<style scoped>
.container {
  min-height: 100vh;
  padding: 20px;
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 50%, #9B8FF8 100%);
  position: relative;
}

.container::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: repeating-linear-gradient(45deg, transparent, transparent 35px, rgba(255,255,255,0.05) 35px, rgba(255,255,255,0.05) 70px);
  pointer-events: none;
  z-index: 0;
}

.container > * {
  position: relative;
  z-index: 1;
}

.header {
  background: white;
  padding: 15px 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
}

.header h1 {
  font-size: 24px;
  color: #6B5DD3;
  margin: 0;
}

.back-btn {
  color: #6B5DD3;
  text-decoration: none;
  font-size: 24px;
  padding: 8px 12px;
  background: rgba(107, 93, 211, 0.1);
  border-radius: 8px;
  transition: all 0.3s;
}

.back-btn:hover {
  background: rgba(107, 93, 211, 0.2);
  transform: scale(1.1);
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-group label {
  font-size: 13px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 5px;
}

.test-dir-select {
  padding: 8px 14px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  min-width: 133px;
  max-width: 400px;
  width: auto;
}

.test-dir-select:hover {
  border-color: #6B5DD3;
}

.btn-compact {
  padding: 6px 12px !important;
  font-size: 12px !important;
  width: auto !important;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 20px;
  background: #f5f5f5;
  border-radius: 6px;
  font-size: 14px;
  font-weight: normal;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ccc;
  animation: pulse 2s infinite;
}

.status-dot.connected {
  background: #4caf50;
}

.status-dot.error {
  background: #f44336;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
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

.charts-container {
  display: grid;
  gap: 15px;
  margin-bottom: 20px;
}

.charts-container.columns-2 {
  grid-template-columns: repeat(2, 1fr);
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

.metadata-section {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.metadata-section h3 {
  font-size: 18px;
  color: #333;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #f0f0f0;
}

.metadata-content {
  font-size: 14px;
  line-height: 1.8;
  color: #666;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.stat-row:last-child {
  border-bottom: none;
}

.stat-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #6B5DD3;
}

@media (max-width: 768px) {
  .header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-controls {
    width: 100%;
    justify-content: space-between;
  }

  .charts-container.columns-2 {
    grid-template-columns: 1fr;
  }
}
</style>
