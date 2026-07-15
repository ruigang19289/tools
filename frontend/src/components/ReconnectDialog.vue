<template>
  <!-- 重新连接对话框 -->
  <div v-if="showReconnectDialog" class="dialog-overlay">
    <div class="dialog">
      <h3>检测到上次连接</h3>
      <p>上次连接了以下主机：</p>
      <strong v-html="reconnectHosts" style="display: block; margin: 15px 0; line-height: 1.8;"></strong>
      <p>是否重新连接？</p>
      <div class="dialog-actions">
        <button class="btn-secondary" @click="handleReconnectNo">否</button>
        <button class="btn-primary" @click="handleReconnectYes">是</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'

// Props - 外部传入
const props = defineProps({
  apiEndpoint: {
    type: String,
    required: true
  },
  storageKey: {
    type: String,
    required: true
  },
  onReconnect: {
    type: Function,
    required: true
  },
  autoReconnect: {
    type: Boolean,
    default: false
  }
})

const normalizeKey = (suffix) => `${props.storageKey}_${suffix}`

const clearStoredReconnectState = () => {
  localStorage.removeItem(normalizeKey('connection_history'))
  localStorage.removeItem(normalizeKey('server_start_time'))
}

// Emits
const emit = defineEmits(['close'])

// 状态
const showReconnectDialog = ref(false)
const reconnectHosts = ref('')
const reconnectHistory = ref([])

// 保存服务启动时间
const saveServerTime = async () => {
  try {
    const res = await fetch(`${props.apiEndpoint}/server-info`)
    const info = await res.json()
    localStorage.setItem(normalizeKey('server_start_time'), info.server_start_time)
  } catch (e) {
    console.error('Failed to save server time:', e)
  }
}

// 提示重新连接
const promptReconnect = async () => {
  const saved = localStorage.getItem(normalizeKey('connection_history'))
  if (!saved) return

  try {
    // Get current server time
    const serverInfoRes = await fetch(`${props.apiEndpoint}/server-info`)
    const serverInfo = await serverInfoRes.json()
    const currentServerTime = serverInfo.server_start_time

    // Get saved server time
    const savedServerTime = localStorage.getItem(normalizeKey('server_start_time'))

    // If server has restarted (time mismatch), clear history and return
    if (savedServerTime && parseFloat(savedServerTime) !== currentServerTime) {
      console.log('Server restarted, clearing connection history')
      clearStoredReconnectState()
      return
    }

    const history = JSON.parse(saved)
    if (history.length === 0) return

    reconnectHistory.value = history
    reconnectHosts.value = history.map(h =>
      `<span style="color: #333;">${h.username}@${h.host}</span>`
    ).join('<br>')

    if (props.autoReconnect) {
      await handleReconnectYes()
      return
    }

    // Show reconnect dialog
    showReconnectDialog.value = true
  } catch (error) {
    console.error('promptReconnect error:', error)
  }
}

// 处理重新连接 - 是
const handleReconnectYes = async () => {
  showReconnectDialog.value = false

  if (reconnectHistory.value.length === 0) return

  // Call external reconnect handler
  await props.onReconnect(reconnectHistory.value)

  // Save server time
  await saveServerTime()
}

// 处理重新连接 - 否
const handleReconnectNo = () => {
  showReconnectDialog.value = false
  clearStoredReconnectState()
}

// 保存连接历史
const saveConnectionHistory = async () => {
  const history = props.history
  if (!history || history.length === 0) return

  localStorage.setItem(normalizeKey('connection_history'), JSON.stringify(history))
  await saveServerTime()
}

// 清除连接历史
const clearConnectionHistory = () => {
  clearStoredReconnectState()
}

// 初始化
onMounted(async () => {
  // 等待 DOM 和父组件准备好
  await nextTick()
  setTimeout(() => {
    promptReconnect()
  }, 300)
})

// Expose methods
defineExpose({
  promptReconnect,
  saveConnectionHistory,
  clearConnectionHistory,
  saveServerTime
})
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dialog {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  min-width: 400px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.dialog h3 {
  margin: 0 0 20px 0;
  color: #333;
}

.dialog p {
  color: #666;
  margin-bottom: 20px;
}

.dialog-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn-primary, .btn-secondary {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: #f44336;
  color: white;
}

.btn-secondary:hover {
  background: #da190b;
  transform: translateY(-2px);
}
</style>
