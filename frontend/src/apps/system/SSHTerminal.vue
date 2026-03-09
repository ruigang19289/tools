<template>
  <div class="ssh-page">
    <PageHeader
      icon="💻"
      title="终端连接"
    />

    <!-- Main Content -->
    <div class="main-content">
      <!-- Left Panel -->
      <div class="left-panel">
        <!-- SSH Connection -->
        <div class="section">
          <h2 class="section-title">SSH 连接</h2>

          <div class="form-group">
            <label>远程主机:</label>
            <input type="text" v-model="connection.host" placeholder="192.168.1.1" :disabled="connecting">
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>端口:</label>
              <input type="number" v-model="connection.port" placeholder="22">
            </div>
            <div class="form-group">
              <label>用户名:</label>
              <input type="text" v-model="connection.username" placeholder="root">
            </div>
          </div>

          <div class="form-group">
            <label>密码:</label>
            <input type="password" v-model="connection.password" placeholder="******" @keyup.enter="connectSSH">
          </div>

          <div class="btn-group">
            <button class="btn btn-primary btn-full" @click="connectSSH" :disabled="connecting || !isFormValid">
              {{ connecting ? '连接中...' : '连接' }}
            </button>
          </div>
        </div>

        <!-- File Manager -->
        <div class="section">
          <h2 class="section-title">文件管理</h2>

          <div v-if="!fmSessionId">
            <div class="form-group">
              <label>远程主机:</label>
              <input type="text" v-model="fmConnection.host" placeholder="192.168.1.1">
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>端口:</label>
                <input type="number" v-model="fmConnection.port" placeholder="22">
              </div>
              <div class="form-group">
                <label>用户名:</label>
                <input type="text" v-model="fmConnection.username" placeholder="root">
              </div>
            </div>

            <div class="form-group">
              <label>密码:</label>
              <input type="password" v-model="fmConnection.password" placeholder="******" @keyup.enter="connectFM">
            </div>

            <div class="btn-group">
              <button class="btn btn-primary btn-full" @click="connectFM" :disabled="fmConnecting || !isFmFormValid">
                {{ fmConnecting ? '连接中...' : '连接' }}
              </button>
            </div>
          </div>

          <div v-else class="file-content">
            <div class="path-bar">
              <span class="path-label">路径:</span>
              <span class="path-value">{{ currentPath }}</span>
            </div>

            <div class="file-toolbar">
              <button class="btn btn-small" @click="goParent">上级</button>
              <button class="btn btn-small" @click="refreshFiles">刷新</button>
              <button class="btn btn-small" @click="showCreateFolder = true">新建文件夹</button>
              <button class="btn btn-small" @click="triggerUpload">上传</button>
              <button class="btn btn-small btn-danger" @click="disconnectFM">断开</button>
            </div>

            <div class="file-list">
              <div v-if="currentPath !== '/'" class="file-item parent" @click="goParent">
                <span class="file-icon">⬆️</span>
                <span class="file-name">..</span>
              </div>
              <div v-for="f in fileList" :key="f.name" :class="['file-item', { selected: selectedFile?.name === f.name }]" @click="selectedFile = f" @dblclick="handleFileDbClick(f)">
                <span class="file-icon">{{ f.type === 'directory' ? '📁' : '📄' }}</span>
                <span class="file-name">{{ f.name }}</span>
                <span class="file-size">{{ f.size }}</span>
              </div>
            </div>

            <div v-if="fileList.length === 0" class="empty-hint">空目录</div>
          </div>
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
          <div v-if="sessions.length > 0" class="host-tabs">
            <div
              v-for="(s, index) in sessions"
              :key="s.tabId"
              class="host-tab"
              :class="{ active: activeTabId === s.tabId }"
              draggable="true"
              @dragstart="handleDragStart(index, $event)"
              @dragover.prevent="handleDragOver(index, $event)"
              @drop="handleDrop(index, $event)"
              @dragend="handleDragEnd"
              @click="switchTab(s.tabId)"
            >
              {{ (s.type === 'ssh' ? 's' : 'f') + s.host }} <span style="margin-left: 8px; opacity: 0.6;" @click.stop="closeTab(s.tabId)">×</span>
            </div>
          </div>

          <div class="terminal-window" ref="terminalWindow">
            <div v-if="sessions.length === 0" class="terminal-empty">
              输入 SSH 连接信息或文件管理信息后点击"连接"按钮
            </div>
            <div v-for="s in sessions.filter(x => x.type === 'ssh')" :key="s.tabId" v-show="activeTabId === s.tabId" :id="'terminal-' + s.tabId" class="terminal-div"></div>
          </div>

          <!-- File Manager (outside terminal-window) -->
          <div v-for="s in sessions.filter(x => x.type === 'file')" :key="s.tabId" v-show="activeTabId === s.tabId" class="file-manager-wrapper">
            <div class="file-manager-content">
              <div class="path-bar">
                <span class="path-label">路径:</span>
                <span class="path-value">{{ s.currentPath || '/root' }}</span>
              </div>

              <div class="file-toolbar">
                <button class="btn btn-small" @click="goParent(s.tabId)">上级</button>
                <button class="btn btn-small" @click="refreshFiles(s.tabId)">刷新</button>
                <button class="btn btn-small" @click="showCreateFolderDialog(s.tabId)">新建文件夹</button>
                <button class="btn btn-small" @click="triggerUpload(s.tabId)">上传</button>
              </div>

              <div class="file-list">
                <div v-if="s.currentPath !== '/'" class="file-item parent" @click="goParent(s.tabId)">
                  <span class="file-icon">⬆️</span>
                  <span class="file-name">..</span>
                </div>
                <div v-for="f in s.fileList || []" :key="f.name" :class="['file-item', { selected: s.selectedFile?.name === f.name }]" @click="selectFile(s.tabId, f)" @dblclick="handleFileDbClick(s.tabId, f)">
                  <span class="file-icon">{{ f.type === 'directory' ? '📁' : '📄' }}</span>
                  <span class="file-name">{{ f.name }}</span>
                  <span class="file-size">{{ f.size }}</span>
                </div>
              </div>

              <div v-if="!s.fileList || s.fileList.length === 0" class="empty-hint">空目录</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Folder Dialog -->
    <div v-if="showCreateFolder" class="modal-overlay" @click.self="showCreateFolder = false">
      <div class="modal">
        <h3>新建文件夹</h3>
        <input type="text" v-model="newFolderName" placeholder="文件夹名称" @keyup.enter="createFolder">
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showCreateFolder = false">取消</button>
          <button class="btn btn-primary" @click="createFolder">创建</button>
        </div>
      </div>
    </div>

    <!-- Upload Input -->
    <input ref="fileInput" type="file" style="display:none" @change="handleUpload">

    <!-- Notification -->
    <div class="notification" :class="notification.type" v-if="notification.show">
      {{ notification.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import PageHeader from '@/components/common/PageHeader.vue'

// Connection
const connection = reactive({ host: '', port: '22', username: 'root', password: '' })
const connecting = ref(false)
const sessions = ref([])
const activeTabId = ref(null)
const notification = reactive({ show: false, message: '', type: 'info' })

// File Manager Connection
const fmConnection = reactive({ host: '', port: '22', username: 'root', password: '' })
const fmConnecting = ref(false)
const fmSessionId = ref(null)

// File Manager
const fileList = ref([])
const currentPath = ref('/root')
const selectedFile = ref(null)
const showCreateFolder = ref(false)
const newFolderName = ref('')
const fileInput = ref(null)

// WebSocket & Terminals
const wsConnections = {}
const terminals = {}
let tabCounter = 0

const isFormValid = computed(() => connection.host.trim() && connection.username.trim() && connection.password)

const isFmFormValid = computed(() => fmConnection.host.trim() && fmConnection.username.trim() && fmConnection.password)

const showNotification = (message, type = 'info') => {
  notification.message = message
  notification.type = type
  notification.show = true
  setTimeout(() => { notification.show = false }, 3000)
}

// Terminal Functions
const createTerminal = (tabId, sessionId) => {
  const term = new Terminal({
    cursorBlink: true, fontSize: 14, fontFamily: 'Consolas, monospace',
    theme: { background: '#000000', foreground: '#ffffff' }, rows: 30, cols: 100
  })
  const fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  const div = document.getElementById('terminal-' + tabId)
  if (div) { term.open(div); fitAddon.fit(); term.writeln(`\x1b[1;32mConnected to session\x1b[0m`) }
  term.onData((data) => {
    const ws = wsConnections[tabId]
    if (ws?.readyState === WebSocket.OPEN && sessionId) {
      ws.send(JSON.stringify({ action: 'input', session_id: sessionId, data }))
    }
  })
  terminals[tabId] = { term, fitAddon }
}

const connectSSH = async () => {
  if (!isFormValid.value) return
  connecting.value = true
  const tabId = `tab-${++tabCounter}`
  sessions.value.push({ tabId, host: connection.host, type: 'ssh', sessionId: null })
  switchTab(tabId)

  try {
    const res = await fetch('/api/v1/system/ssh/connect', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host: connection.host, port: parseInt(connection.port), username: connection.username, password: connection.password })
    })
    const data = await res.json()
    if (data.status === 'success') {
      const s = sessions.value.find(x => x.tabId === tabId)
      if (s) { s.sessionId = data.session_id }
      showNotification(`已连接到 ${connection.host}`, 'success')
      await nextTick()
      createTerminal(tabId, data.session_id)
      connectWebSocket(tabId, data.session_id)
    } else {
      showNotification(`连接失败: ${data.error}`, 'error')
      closeTab(tabId)
    }
  } catch (e) {
    showNotification(`错误: ${e.message}`, 'error')
    closeTab(tabId)
  } finally {
    connecting.value = false
  }
}

const connectWebSocket = (tabId, sessionId) => {
  const ws = new WebSocket(`ws://${window.location.host}/api/ssh/ws`)
  wsConnections[tabId] = ws
  ws.onopen = () => ws.send(JSON.stringify({ action: 'connect', session_id: sessionId }))
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data)
    const term = terminals[tabId]?.term
    if (data.type === 'output' && term) term.write(data.data)
    else if (data.type === 'closed' && term) term.writeln('\r\n\x1b[31mDisconnected\x1b[0m')
    else if (data.type === 'error') showNotification(data.error, 'error')
  }
  ws.onclose = () => delete wsConnections[tabId]
}

const switchTab = (tabId) => {
  activeTabId.value = tabId
  if (terminals[tabId]) {
    nextTick(() => {
      terminals[tabId]?.fitAddon?.fit()
    })
  }
}

// Drag and Drop for tabs
let draggedIndex = null

const handleDragStart = (index, event) => {
  draggedIndex = index
  event.dataTransfer.effectAllowed = 'move'
  event.target.style.opacity = '0.5'
}

const handleDragOver = (index, event) => {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

const handleDrop = (index, event) => {
  event.preventDefault()
  if (draggedIndex !== null && draggedIndex !== index) {
    const newSessions = [...sessions.value]
    const draggedItem = newSessions[draggedIndex]
    newSessions.splice(draggedIndex, 1)
    newSessions.splice(index, 0, draggedItem)
    sessions.value = newSessions
  }
}

const handleDragEnd = (event) => {
  event.target.style.opacity = '1'
  draggedIndex = null
}

const closeTab = async (tabId) => {
  const s = sessions.value.find(x => x.tabId === tabId)
  if (s?.sessionId) {
    try { await fetch('/api/v1/system/ssh/disconnect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: s.sessionId }) }) } catch (e) {}
  }
  if (wsConnections[tabId]) { wsConnections[tabId].close(); delete wsConnections[tabId] }
  terminals[tabId]?.term?.dispose()
  delete terminals[tabId]
  sessions.value = sessions.value.filter(x => x.tabId !== tabId)
  if (activeTabId.value === tabId && sessions.value.length > 0) switchTab(sessions.value[0].tabId)
}

// File Manager Functions
const doFetch = async (url, body) => {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  return res.json()
}

const connectFM = async () => {
  if (!fmConnection.host || !fmConnection.username || !fmConnection.password) {
    showNotification('请填写完整连接信息', 'error')
    return
  }
  fmConnecting.value = true
  const tabId = `tab-${++tabCounter}`

  try {
    const res = await fetch('/api/v1/system/ssh/connect', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host: fmConnection.host, port: parseInt(fmConnection.port), username: fmConnection.username, password: fmConnection.password })
    })
    const data = await res.json()
    if (data.status === 'success') {
      sessions.value.push({
        tabId,
        host: fmConnection.host,
        type: 'file',
        sessionId: data.session_id,
        currentPath: '/root',
        fileList: [],
        selectedFile: null
      })
      switchTab(tabId)
      showNotification(`已连接到 ${fmConnection.host}`, 'success')
      await listFiles(tabId, '/root')
    } else {
      showNotification(`连接失败: ${data.error}`, 'error')
    }
  } catch (e) {
    showNotification(`错误: ${e.message}`, 'error')
  } finally {
    fmConnecting.value = false
  }
}

const disconnectFM = async () => {
  if (fmSessionId.value) {
    try {
      await fetch('/api/v1/system/ssh/disconnect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: fmSessionId.value }) })
    } catch (e) {}
  }
  fmSessionId.value = null
  fileList.value = []
  currentPath.value = '/root'
  showNotification('已断开文件管理连接', 'info')
}

const listFiles = async (tabId, path) => {
  const session = sessions.value.find(s => s.tabId === tabId)
  if (!session || !session.sessionId) return

  const data = await doFetch('/api/v1/system/filemanager/list', { session_id: session.sessionId, path })
  if (data.status === 'success') {
    session.fileList = data.items || []
    session.currentPath = data.path
  }
}

const goParent = (tabId) => {
  const session = sessions.value.find(s => s.tabId === tabId)
  if (!session || session.currentPath === '/') return
  const parts = session.currentPath.split('/').filter(x => x)
  parts.pop()
  listFiles(tabId, parts.length ? '/' + parts.join('/') : '/')
}

const refreshFiles = (tabId) => {
  const session = sessions.value.find(s => s.tabId === tabId)
  if (session) listFiles(tabId, session.currentPath)
}

const handleFileDbClick = (tabId, f) => {
  if (f.type === 'directory') {
    const session = sessions.value.find(s => s.tabId === tabId)
    if (session) {
      const newPath = `${session.currentPath}/${f.name}`.replace('//', '/')
      listFiles(tabId, newPath)
    }
  }
}

const selectFile = (tabId, f) => {
  const session = sessions.value.find(s => s.tabId === tabId)
  if (session) session.selectedFile = f
}

const showCreateFolderDialog = (tabId) => {
  activeTabId.value = tabId
  showCreateFolder.value = true
}

const createFolder = async () => {
  if (!newFolderName.value.trim()) return
  const session = sessions.value.find(s => s.tabId === activeTabId.value)
  if (!session || !session.sessionId) return showNotification('未连接', 'error')

  const data = await doFetch('/api/v1/system/filemanager/mkdir', {
    session_id: session.sessionId,
    path: session.currentPath,
    dir_name: newFolderName.value
  })
  if (data.status === 'success') {
    showNotification('创建成功', 'success')
    newFolderName.value = ''
    showCreateFolder.value = false
    refreshFiles(activeTabId.value)
  }
  else showNotification(`失败: ${data.error}`, 'error')
}

let uploadTabId = null

const triggerUpload = (tabId) => {
  uploadTabId = tabId
  nextTick(() => fileInput.value?.click())
}

const handleUpload = async (e) => {
  const file = e.target.files[0]
  if (!file) return

  const session = sessions.value.find(s => s.tabId === uploadTabId)
  if (!session || !session.sessionId) return showNotification('未连接', 'error')

  showNotification(`上传 ${file.name}...`, 'info')
  try {
    const init = await doFetch('/api/v1/system/filemanager/upload/init', {
      session_id: session.sessionId,
      path: session.currentPath,
      filename: file.name,
      totalChunks: 1
    })
    if (init.status !== 'success') throw new Error(init.error)

    const reader = new FileReader()
    reader.onload = async () => {
      const chunk = await doFetch('/api/v1/system/filemanager/upload/chunk', {
        task_id: init.task_id,
        chunkIndex: 0,
        chunkData: reader.result.split(',')[1]
      })
      if (chunk.status === 'success') {
        showNotification('上传成功', 'success')
        refreshFiles(uploadTabId)
      } else {
        throw new Error(chunk.error)
      }
    }
    reader.readAsDataURL(file)
  } catch (err) {
    showNotification(`上传失败: ${err.message}`, 'error')
  }
  e.target.value = ''
}

onMounted(() => {
  const saved = localStorage.getItem('ssh_connection_history')
  if (saved) {
    try { const hist = JSON.parse(saved)[0]; if (hist) { connection.host = hist.host; connection.username = hist.username; connection.password = hist.password || '' } } catch (e) {}
  }
})
</script>

<style scoped>
.ssh-page { min-height: 100vh; padding: 20px; background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 50%, #9B8FF8 100%); position: relative; }
.ssh-page::before { content: ''; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: repeating-linear-gradient(45deg, transparent, transparent 35px, rgba(255,255,255,0.05) 35px, rgba(255,255,255,0.05) 70px); pointer-events: none; z-index: 0; }
.ssh-page > * { position: relative; z-index: 1; }

.main-content { display: grid; grid-template-columns: 320px 1fr; gap: 20px; align-items: start; }
.left-panel { display: flex; flex-direction: column; gap: 15px; }
.right-panel {
  display: flex;
  flex-direction: column;
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

.terminal-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
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

.terminal-window {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 15px;
  height: 705px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.terminal-empty {
  color: #666;
  text-align: center;
  padding: 20px;
}

.terminal-div {
  height: 100%;
  width: 100%;
  margin: 0;
  padding: 0;
  background: transparent;
}

.terminal-div .xterm {
  height: 100%;
  padding: 0;
}

.terminal-div .xterm-viewport {
  background-color: transparent !important;
}

.file-manager-content {
  background: white;
  padding: 20px;
  height: 705px;
  overflow-y: auto;
  color: #333;
  border-radius: 8px;
}

.section { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); flex: 1; display: flex; flex-direction: column; }
.section-title { font-size: 18px; font-weight: 600; color: #333; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }

.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 13px; color: #666; margin-bottom: 4px; }
.form-group input { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

.btn-group { display: flex; flex-direction: column; gap: 8px; margin-top: 15px; }

/* Session List */
.session-list { display: flex; flex-direction: column; gap: 8px; }
.session-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: #f5f5f5; border-radius: 6px; cursor: pointer; }
.session-item:hover { background: #f0f4ff; }
.session-item.active { background: #6B5DD3; color: white; }
.session-host { font-size: 13px; }
.close-btn { font-size: 16px; opacity: 0.7; }
.close-btn:hover { opacity: 1; }

/* File Manager */
.path-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; padding: 8px 12px; background: #f5f5f5; border-radius: 6px; font-size: 12px; }
.path-label { color: #666; }
.path-value { color: #6B5DD3; font-family: monospace; }

.file-toolbar { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }

.file-list { max-height: 600px; overflow-y: auto; }
.file-item { display: grid; grid-template-columns: 32px 1fr 60px; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 6px; cursor: pointer; color: #333; }
.file-item:hover { background: #f5f5f5; }
.file-item.selected { background: #6B5DD3; color: white; }
.file-item.parent { background: #f9f9f9; }
.file-icon { font-size: 18px; }
.file-name { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { font-size: 11px; color: #999; }
.file-item.selected .file-size { color: rgba(255,255,255,0.8); }

.file-empty { display: flex; align-items: center; justify-content: center; height: 100px; color: #999; font-size: 14px; }

.empty-hint { text-align: center; color: #999; padding: 10px; font-size: 13px; }

/* Tabs */
.tabs-bar {
  background: white;
  padding: 0;
  box-shadow: none;
  border-bottom: 2px solid #e0e0e0;
}
.tabs-placeholder {
  text-align: center;
  color: #999;
  padding: 10px;
  font-size: 13px;
}
.tabs-list {
  display: flex;
  gap: 5px;
  padding: 0 20px;
}
.tab-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  cursor: move;
  font-size: 13px;
  color: #666;
  transition: all 0.3s;
  user-select: none;
}
.tab-item:hover {
  background: #e8e8e8;
  color: #333;
}
.tab-item.active {
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 100%);
  color: white;
  border-color: #6B5DD3;
  font-weight: 600;
}
.tab-item[draggable="true"] {
  cursor: move;
}
.tab-item:active {
  cursor: grabbing;
}
.tab-label { font-weight: 500; }
.tab-item .close-btn {
  font-size: 18px;
  font-weight: bold;
  opacity: 0.6;
  transition: opacity 0.2s;
  margin-left: 8px;
}
.tab-item .close-btn:hover { opacity: 1; }

/* Content Area */
.content-area {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 0 0 12px 12px;
  flex: 1;
  min-height: calc(100vh - 200px);
  overflow: hidden;
  position: relative;
}

/* Terminal */
.terminal-wrapper {
  display: none;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}
.terminal-wrapper.active { display: block; }

/* File Manager */
.file-manager-wrapper {
  display: none;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow-y: auto;
}
.file-manager-wrapper.active { display: block; }

.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; color: #999; }
.empty-icon { font-size: 64px; margin-bottom: 15px; }

/* Modal */
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: white; padding: 24px; border-radius: 12px; min-width: 300px; }
.modal h3 { margin: 0 0 16px 0; color: #333; }
.modal input { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 16px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; }

/* Notification */
.notification { position: fixed; top: 80px; right: 20px; padding: 12px 20px; border-radius: 8px; color: white; font-size: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000; }
.notification.success { background: linear-gradient(135deg, #27ae60, #2ecc71); }
.notification.error { background: linear-gradient(135deg, #c0392b, #e74c3c); }

@media (max-width: 1024px) { .main-content { grid-template-columns: 1fr; } }
</style>
