<template>
  <div class="ping-page">
    <PageHeader
      icon="🌐"
      title="网段扫描"
    />

    <!-- Main Content -->
    <div class="main-content">
      <!-- Left Panel: Config -->
      <div class="left-panel">
        <div class="section">
          <h2 class="section-title">扫描配置</h2>

          <div class="form-group">
            <label>网段或 IP 范围:</label>
            <textarea
              v-model="networkInput"
              placeholder="192.168.1.0/24
或
192.168.1.1-192.168.1.100"
              rows="3"
            ></textarea>
          </div>

          <div class="form-group">
            <label>超时时间 (秒):</label>
            <input type="number" v-model="timeout" placeholder="1" min="1" max="10">
          </div>

          <div class="btn-group">
            <button
              class="btn btn-primary btn-full"
              @click="startScan"
              :disabled="loading || !networkInput.trim()"
            >
              {{ loading ? '扫描中...' : '开始扫描' }}
            </button>
            <button
              v-if="scanId"
              class="btn btn-danger btn-full"
              @click="cancelScan"
            >
              取消扫描
            </button>
          </div>
        </div>

        <!-- Progress -->
        <div v-if="scanProgress" class="section">
          <h2 class="section-title">扫描进度</h2>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
          <div class="progress-info">
            <span>{{ progressPercent }}%</span>
            <span>{{ scanProgress.scanned }}/{{ scanProgress.total }}</span>
          </div>
          <div class="progress-stats">
            <span class="stat online">🟢 在线: {{ scanProgress.online }}</span>
            <span class="stat offline">🔴 离线: {{ scanProgress.offline }}</span>
            <span class="stat timeout">🟡 超时: {{ scanProgress.timeout || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- Right Panel: Results -->
      <div class="right-panel">
        <div v-if="results.length > 0" class="section result-section">
          <div class="section-header">
            <h2 class="section-title">扫描结果</h2>
            <span class="result-count">{{ onlineCount }} 在线 / {{ results.length }} 总数</span>
          </div>

          <div class="results-grid">
            <div
              v-for="(item, idx) in sortedResults"
              :key="idx"
              :class="['result-block', item.status]"
              :title="`${item.ip}${item.response_time ? ' - ' + item.response_time + 'ms' : ''}`"
            >
              <div class="block-ip">{{ item.ip }}</div>
              <div v-if="item.response_time" class="block-time">{{ item.response_time }}ms</div>
            </div>
          </div>
        </div>

        <div v-else class="section empty-section">
          <div class="empty-state">
            <span class="empty-icon">🌐</span>
            <p>输入网段后点击"开始扫描"</p>
            <p class="hint">支持 CIDR 格式或 IP 范围</p>
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
import { ref, reactive, computed } from 'vue'
import api from '@/api'
import PageHeader from '@/components/common/PageHeader.vue'

const API_BASE = `/network/ping`

const networkInput = ref('')
const timeout = ref(1)
const loading = ref(false)
const scanId = ref('')
const results = ref([])
const scanProgress = ref(null)

const notification = reactive({ show: false, message: '', type: 'info' })

const onlineCount = computed(() => results.value.filter(r => r.status === 'online').length)

const progressPercent = computed(() => {
  if (!scanProgress.value || scanProgress.value.total === 0) return 0
  return Math.round((scanProgress.value.scanned / scanProgress.value.total) * 100)
})

// 排序结果：在线的按 IP 排序到前面
const sortedResults = computed(() => {
  const sorted = [...results.value]

  // IP 地址转换为数字用于排序
  const ipToNumber = (ip) => {
    const parts = ip.split('.')
    return parts.reduce((acc, part, idx) => {
      return acc + parseInt(part) * Math.pow(256, 3 - idx)
    }, 0)
  }

  return sorted.sort((a, b) => {
    // 在线的排在前面
    if (a.status === 'online' && b.status !== 'online') return -1
    if (a.status !== 'online' && b.status === 'online') return 1

    // 同状态按 IP 排序
    return ipToNumber(a.ip) - ipToNumber(b.ip)
  })
})

const showNotification = (message, type = 'info') => {
  notification.message = message
  notification.type = type
  notification.show = true
  setTimeout(() => { notification.show = false }, 3000)
}

let pollTimer = null

const startScan = async () => {
  if (!networkInput.value.trim()) {
    showNotification('请输入网段', 'error')
    return
  }

  loading.value = true
  results.value = []
  scanId.value = ''

  try {
    const response = await api.post(`${API_BASE}/ping-scan`, {
      network: networkInput.value,
      timeout: timeout.value
    })

    if (response.status === 'started') {
      scanId.value = response.scan_id
      showNotification('扫描已启动', 'success')
      startPolling()
    } else {
      showNotification(response.error || '启动失败', 'error')
    }
  } catch (e) {
    showNotification(e.message || '请求失败', 'error')
  } finally {
    loading.value = false
  }
}

const startPolling = () => {
  pollTimer = setInterval(async () => {
    if (!scanId.value) {
      clearInterval(pollTimer)
      return
    }

    try {
      const response = await api.get(`${API_BASE}/ping-results/${scanId.value}`)

      if (response.status === 'error') {
        showNotification(response.error, 'error')
        clearInterval(pollTimer)
        scanId.value = ''
        return
      }

      scanProgress.value = {
        total: response.total,
        scanned: response.scanned,
        online: response.online,
        offline: response.offline
      }

      results.value = response.results || []

      if (response.status === 'completed' || response.status === 'error') {
        clearInterval(pollTimer)
        scanId.value = ''
        if (response.status === 'completed') {
          showNotification(`扫描完成: ${response.online} 在线`, 'success')
        }
      }
    } catch (e) {
      console.error('Polling error:', e)
    }
  }, 500)
}

const cancelScan = async () => {
  if (!scanId.value) return
  try {
    await api.delete(`${API_BASE}/ping-cancel/${scanId.value}`)
    clearInterval(pollTimer)
    scanId.value = ''
    showNotification('扫描已取消', 'info')
  } catch (e) {
    showNotification('取消失败', 'error')
  }
}
</script>

<style scoped>
.ping-page { min-height: 100vh; padding: 20px; background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 50%, #9B8FF8 100%); position: relative; }
.ping-page::before { content: ''; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: repeating-linear-gradient(45deg, transparent, transparent 35px, rgba(255,255,255,0.05) 35px, rgba(255,255,255,0.05) 70px); pointer-events: none; z-index: 0; }
.ping-page > * { position: relative; z-index: 1; }

.header { background: white; padding: 15px 20px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); border-radius: 12px; margin-bottom: 20px; }
.header .back-btn { color: #6B5DD3; text-decoration: none; font-size: 24px; padding: 8px 12px; background: rgba(107,93,211,0.1); border-radius: 8px; }
.header h1 { color: #6B5DD3; font-size: 24px; font-weight: 600; margin: 0; }
.main-content {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  min-height: calc(100vh - 140px);
}

.left-panel, .right-panel { display: flex; flex-direction: column; gap: 15px; }

.section {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.section-title { font-size: 18px; font-weight: 600; color: #333; margin-bottom: 15px; }

.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }

.section-header .section-title { margin-bottom: 0; }

.form-group { margin-bottom: 12px; }

.form-group label { display: block; font-size: 12px; color: #666; margin-bottom: 4px; }

.form-group input, .form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  font-family: monospace;
}

.form-group textarea { resize: vertical; }

.btn-group { display: flex; flex-direction: column; gap: 8px; margin-top: 15px; }

.progress-bar {
  height: 20px;
  background: #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  transition: width 0.3s;
}

.progress-info { display: flex; justify-content: space-between; font-size: 13px; color: #666; margin-bottom: 10px; }

.progress-stats { display: flex; gap: 15px; }

.stat { font-size: 13px; font-weight: 500; }

.stat.online { color: #27ae60; }

.stat.offline { color: #e74c3c; }

.result-section { flex: 1; }

.result-count { font-size: 14px; color: #666; }

.results-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 8px;
  max-height: 600px;
  overflow-y: auto;
}

.result-block {
  height: 60px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px 4px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.result-block.online {
  background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%);
  color: white;
  border-color: #4CAF50;
}

.result-block.offline {
  background: linear-gradient(135deg, #f44336 0%, #e57373 100%);
  color: white;
  border-color: #f44336;
}

.result-block.timeout {
  background: linear-gradient(135deg, #ff9800 0%, #ffb74d 100%);
  color: white;
  border-color: #ff9800;
}

.result-block.scanning {
  background: #fff3e0;
  color: #ff9800;
  border-color: #ffb74d;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.result-block:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.block-ip {
  font-weight: 600;
  font-size: 10px;
  margin-bottom: 2px;
  text-align: center;
  line-height: 1.2;
  word-break: break-all;
}

.block-time {
  font-size: 9px;
  opacity: 0.9;
}

.empty-section { flex: 1; display: flex; align-items: center; justify-content: center; }

.empty-state { text-align: center; color: #999; }

.empty-icon { font-size: 64px; margin-bottom: 15px; display: block; }

.empty-state .hint { font-size: 13px; color: #bbb; margin-top: 10px; }

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

.notification.success { background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); }

.notification.error { background: linear-gradient(135deg, #c0392b 0%, #e74c3c 100%); }

@media (max-width: 1024px) {
  .main-content { grid-template-columns: 1fr; }
}
</style>
