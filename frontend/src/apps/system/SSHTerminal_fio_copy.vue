<template>
  <div class="fio-page">
    <PageHeader
      icon="💻"
      title="终端连接"
    />

    <!-- Main Content -->
    <div class="main-content">
      <!-- Left Panel: Configuration -->
      <div class="left-panel">
        <!-- Host Configuration -->
        <div class="section">
          <h2 class="section-title">SSH连接</h2>

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

        <!-- File Manager -->
        <div class="section">
          <h2 class="section-title">文件管理器</h2>

          <div class="form-group">
            <label>远程主机 (每行一个):</label>
            <textarea
              v-model="hostsTextFile"
              placeholder="192.168.1.1
192.168.1.2
192.168.1.3"
              rows="3"
            ></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>端口:</label>
              <input type="number" v-model="configFile.port" placeholder="22">
            </div>
            <div class="form-group">
              <label>用户名:</label>
              <input type="text" v-model="configFile.username" placeholder="root">
            </div>
          </div>

          <div class="form-group">
            <label>密码:</label>
            <input type="password" v-model="configFile.password" placeholder="******">
          </div>

          <button class="btn btn-primary btn-full" @click="validateHostsFile" :disabled="!canValidateFile">
            验证连接
          </button>

          <div v-if="validationResultsFile.length > 0" class="validation-summary">
            <span class="badge success" v-if="validationResultsFile.every(r => r.status === 'success')">
              ✅ 全部连接成功
            </span>
            <span class="badge warning" v-else-if="validationResultsFile.some(r => r.status === 'success')">
              ⚠️ 部分成功 ({{ validationResultsFile.filter(r => r.status === 'success').length }}/{{ getValidHostsFile().length }})</span>
            <span class="badge error" v-else>
              ❌ 连接失败
            </span>
          </div>
        </div>
      </div>

      <!-- Right Panel: Terminal -->
      <div class="right-panel">
        <!-- Terminal Output -->
        <div class="terminal-section">
          <div class="terminal-header">
            <div class="terminal-title-group">
              <span class="terminal-title">终端输出</span>
            </div>
          </div>

          <!-- Host Tabs -->
          <div v-if="connectedHosts.length > 0" class="host-tabs">
            <div
              v-for="host in connectedHosts"
              :key="host"
              class="host-tab"
              :class="{ active: activeHostTab === host }"
              @click="activeHostTab = host"
              draggable="true"
              @dragstart="handleDragStart($event, host)"
              @dragover.prevent
              @drop="handleDrop($event, host)"
            >
              {{ getHostDisplayName(host) }}
              <span class="tab-close" @click.stop="closeTab(host)">×</span>
            </div>
          </div>

          <div class="terminal-window" ref="terminalWindow">
            <div v-if="!activeHostTab" class="terminal-empty">
              输入连接信息后点击"验证连接"按钮
            </div>

            <!-- SSH Terminal: Xterm container for each SSH host -->
            <div
              v-for="hostKey in connectedHosts.filter(h => h.startsWith('s'))"
              :key="hostKey"
              :ref="el => { if (el) terminalRefs[hostKey] = el }"
              class="xterm-container"
              :style="{ display: activeHostTab === hostKey ? 'block' : 'none' }"
            ></div>

            <!-- File Manager: File browser for each file host -->
            <div
              v-for="hostKey in connectedHosts.filter(h => h.startsWith('f'))"
              :key="hostKey"
              class="file-manager-container"
              :style="{ display: activeHostTab === hostKey ? 'block' : 'none' }"
            >
              <div class="file-manager-header">
                <div class="path-bar">
                  <span class="path-label">当前路径:</span>
                  <span class="path-value">{{ fileManagers[hostKey]?.currentPath || '/' }}</span>
                </div>
                <div class="file-actions">
                  <button class="btn btn-compact" @click="refreshFiles(hostKey)">刷新</button>
                  <button class="btn btn-compact" @click="triggerUpload(hostKey)">上传文件</button>
                  <input
                    type="file"
                    :ref="el => { if (el) uploadInputs[hostKey] = el }"
                    style="display: none"
                    @change="handleFileUpload($event, hostKey)"
                  />
                </div>
              </div>

              <!-- Upload Progress Bar -->
              <div v-if="fileManagers[hostKey]?.uploading" class="upload-progress">
                <div class="upload-info">
                  <span class="upload-filename">上传: {{ fileManagers[hostKey].uploadFileName }}</span>
                  <span class="upload-percent">{{ fileManagers[hostKey].uploadProgress }}%</span>
                </div>
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: fileManagers[hostKey].uploadProgress + '%' }"></div>
                </div>
              </div>

              <div class="file-list">
                <div v-if="fileManagers[hostKey]?.loading" class="file-loading">
                  加载中...
                </div>
                <div v-else-if="!fileManagers[hostKey]?.files || fileManagers[hostKey].files.length === 0" class="file-empty">
                  目录为空
                </div>
                <template v-else>
                  <!-- Parent directory -->
                  <div v-if="fileManagers[hostKey]?.currentPath !== '/'" class="file-item parent" @click="goParent(hostKey)">
                    <span class="file-icon">⬆️</span>
                    <span class="file-name">..</span>
                    <span class="file-size"></span>
                    <span class="file-actions-cell"></span>
                  </div>
                  <!-- Files and directories -->
                  <div
                    v-for="file in fileManagers[hostKey].files"
                    :key="file.name"
                    class="file-item"
                    :class="{ directory: file.is_dir }"
                    @dblclick="handleFileDoubleClick(hostKey, file)"
                  >
                    <span class="file-icon">{{ file.is_dir ? '📁' : '📄' }}</span>
                    <span class="file-name">{{ file.name }}</span>
                    <span class="file-size">{{ file.is_dir ? '' : formatFileSize(file.size) }}</span>
                    <span class="file-actions-cell">
                      <button v-if="!file.is_dir" class="btn-icon" @click.stop="downloadFile(hostKey, file)" title="下载">
                        ⬇️
                      </button>
                    </span>
                  </div>
                </template>
              </div>
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
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import PageHeader from '@/components/common/PageHeader.vue'

const API_BASE = `/api/v1/system/ssh`

// WebSocket
let ws = null
const wsConnected = ref(false)
const wsConnections = ref({}) // 每个主机的WebSocket连接

// Xterm instances
const terminalRefs = reactive({}) // DOM refs for xterm containers
const xtermInstances = reactive({}) // Xterm instances for each host

// File Manager
const fileManagers = reactive({}) // File manager state for each host
const uploadInputs = reactive({}) // Upload input refs

// Hosts text
const hostsText = ref('')

// Configuration
const config = reactive({
  username: 'root',
  password: '',
  port: 22
})

// Terminal
const terminalLines = ref([])
const terminalWindow = ref(null)
const hostTerminals = ref({}) // 每个主机的独立终端输出
const activeHostTab = ref('') // 当前激活的主机标签
const draggedHost = ref(null) // For drag and drop

// Validation
const validationResults = ref([])
const connectedHosts = ref([])

// File Manager section
const hostsTextFile = ref('')
const configFile = reactive({
  username: 'root',
  password: '',
  port: 22  // SFTP 默认端口
})
const validationResultsFile = ref([])

// Computed for File Manager
const canValidateFile = computed(() => {
  const validHosts = getValidHostsFile()
  return validHosts.length > 0 && configFile.username && configFile.password
})

// Get valid hosts for File Manager
const getValidHostsFile = () => {
  return hostsTextFile.value
    .split('\n')
    .map(h => h.trim())
    .filter(h => h)
}

// Validate hosts for File Manager
const validateHostsFile = async () => {
  const validHosts = getValidHostsFile()
  addTerminalLine('info', `[文件管理器] 验证 ${validHosts.length} 台主机连接...`)

  try {
    const response = await fetch(`${API_BASE}/validate-hosts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hosts: validHosts,
        username: configFile.username,
        password: configFile.password,
        port: configFile.port,
        type: 'file'
      })
    })

    const data = await response.json()
    validationResultsFile.value = data.results

    // 为每个成功的主机创建唯一的标签（使用时间戳）
    const newHosts = data.results
      .filter(r => r.status === 'success')
      .map(r => {
        const timestamp = Date.now()
        const hostKey = `f${r.host}_${timestamp}`
        return { key: hostKey, host: r.host }
      })

    // 添加到 connectedHosts 并建立文件管理连接
    for (const { key, host } of newHosts) {
      connectedHosts.value.push(key)
      // 初始化文件管理器状态
      fileManagers[key] = {
        sessionId: null,
        currentPath: '/',
        files: [],
        loading: false,
        uploading: false,
        uploadProgress: 0,
        uploadFileName: ''
      }
      // 建立文件管理连接
      await connectFileManager(key, host, configFile.username, configFile.password, configFile.port)
    }

    // 设置最新连接的主机为激活标签
    if (newHosts.length > 0) {
      activeHostTab.value = newHosts[0].key
    }

    data.results.forEach(r => {
      const icon = r.status === 'success' ? '✅' : r.status === 'warning' ? '⚠️' : '❌'
      addTerminalLine(r.status === 'error' ? 'error' : 'info', `[文件管理器] ${icon} ${r.host}: ${r.message}`)
    })

    if (data.results.every(r => r.status === 'success')) {
      showNotification('[文件管理器] 所有主机连接成功', 'success')
    } else {
      showNotification('[文件管理器] 部分主机连接失败', 'warning')
    }
  } catch (error) {
    addTerminalLine('error', `[文件管理器] 验证失败: ${error.message}`)
    showNotification(`[文件管理器] 验证失败: ${error.message}`, 'error')
  }
}

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

// 获取当前激活标签的终端输出
const getCurrentTerminalLines = () => {
  if (activeHostTab.value && hostTerminals.value[activeHostTab.value]) {
    return hostTerminals.value[activeHostTab.value]
  }
  return terminalLines.value
}

// Get host display name
const getHostDisplayName = (hostKey) => {
  // hostKey format: s192.168.1.1_1234567890 or f192.168.1.1_1234567890
  // Extract: s192.168.1.1 or f192.168.1.1
  const match = hostKey.match(/^([sf].+?)_\d+$/)
  return match ? match[1] : hostKey
}

// Close tab
const closeTab = (host) => {
  // Remove from connected hosts
  const index = connectedHosts.value.indexOf(host)
  if (index > -1) {
    connectedHosts.value.splice(index, 1)
  }

  // Remove terminal data
  delete hostTerminals.value[host]

  // Switch to another tab if this was active
  if (activeHostTab.value === host) {
    if (connectedHosts.value.length > 0) {
      activeHostTab.value = connectedHosts.value[0]
    } else {
      activeHostTab.value = ''
    }
  }
}

// Drag and drop handlers
const handleDragStart = (event, host) => {
  draggedHost.value = host
  event.dataTransfer.effectAllowed = 'move'
}

const handleDrop = (event, targetHost) => {
  event.preventDefault()
  if (draggedHost.value && draggedHost.value !== targetHost) {
    const draggedIndex = connectedHosts.value.indexOf(draggedHost.value)
    const targetIndex = connectedHosts.value.indexOf(targetHost)

    if (draggedIndex > -1 && targetIndex > -1) {
      // Swap positions
      const temp = connectedHosts.value[draggedIndex]
      connectedHosts.value[draggedIndex] = connectedHosts.value[targetIndex]
      connectedHosts.value[targetIndex] = temp
    }
  }
  draggedHost.value = null
}

// Send SSH command

// WebSocket functions
const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/ssh/ws`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    wsConnected.value = true
    console.log('SSH WebSocket connected')
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
    console.log('SSH WebSocket disconnected')
  }
}

const handleWebSocketMessage = (message) => {
  const { type, data, host } = message

  if (type === 'output') {
    // 实时输出到终端
    if (data) {
      const lines = data.split('\n')
      lines.forEach(line => {
        if (line.trim()) {
          addTerminalLine('info', line, host)
        }
      })
    }
  } else if (type === 'error') {
    addTerminalLine('error', message.error || '未知错误', host)
  }
}

// Connect SSH via WebSocket
const connectSSH = async (hostKey, host, username, password, port) => {
  return new Promise((resolve, reject) => {
    // Create xterm instance
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 12,
      fontFamily: 'Consolas, "DejaVu Sans Mono", "Courier New", monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#ffffff'
      }
    })

    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)

    // Wait for DOM to be ready
    nextTick(() => {
      const container = terminalRefs[hostKey]
      if (container) {
        term.open(container)
        fitAddon.fit()

        // Store xterm instance
        xtermInstances[hostKey] = { term, fitAddon }
      }
    })

    // Use relative URL to go through Vite proxy in dev, direct in production
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ssh/ws`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      // 发送连接请求
      ws.send(JSON.stringify({
        action: 'connect',
        host: host,
        username: username,
        password: password,
        port: port,
        cols: term.cols,
        rows: term.rows
      }))
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'connected') {
        // 连接成功，保存session_id
        wsConnections.value[hostKey] = {
          ws: ws,
          sessionId: data.session_id
        }
        term.writeln(`\r\n\x1b[32m[${host}] SSH连接已建立\x1b[0m\r\n`)

        // Handle terminal input
        term.onData(input => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              action: 'input',
              session_id: data.session_id,
              data: input
            }))
          }
        })

        resolve()
      } else if (data.type === 'output') {
        // 接收SSH输出
        term.write(data.data)
      } else if (data.type === 'error') {
        term.writeln(`\r\n\x1b[31m[${host}] ${data.error}\x1b[0m\r\n`)
        reject(new Error(data.error))
      } else if (data.type === 'closed') {
        term.writeln(`\r\n\x1b[33m[${host}] SSH连接已关闭\x1b[0m\r\n`)
        ws.close()
      }
    }

    ws.onerror = (error) => {
      term.writeln(`\r\n\x1b[31m[${host}] WebSocket错误\x1b[0m\r\n`)
      reject(error)
    }

    ws.onclose = () => {
      delete wsConnections.value[hostKey]
    }
  })
}

// Send SSH command

const disconnectWebSocket = () => {
  if (ws) {
    ws.close()
    ws = null
    wsConnected.value = false
  }
}

// File Manager Functions
const connectFileManager = async (hostKey, host, username, password, port) => {
  try {
    const response = await fetch(`${API_BASE}/file/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host, username, password, port })
    })

    const data = await response.json()

    if (data.status === 'success') {
      fileManagers[hostKey].sessionId = data.session_id
      // 加载根目录文件列表
      await loadFiles(hostKey, '/')
    } else {
      showNotification(`[文件管理器] ${host} 连接失败: ${data.error}`, 'error')
    }
  } catch (error) {
    showNotification(`[文件管理器] ${host} 连接失败: ${error.message}`, 'error')
  }
}

const loadFiles = async (hostKey, path) => {
  const fm = fileManagers[hostKey]
  if (!fm || !fm.sessionId) {
    console.log('loadFiles: no fm or sessionId', hostKey, fm)
    return
  }

  fm.loading = true

  try {
    // 添加超时控制
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10秒超时

    const response = await fetch(`${API_BASE}/file/list`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: fm.sessionId,
        path: path
      }),
      signal: controller.signal
    })

    clearTimeout(timeoutId)

    const data = await response.json()
    console.log('loadFiles response:', data)

    if (data.status === 'success') {
      fm.currentPath = data.path
      fm.files = data.files
      console.log('Files loaded:', fm.files.length, 'files')
    } else {
      showNotification(`加载文件列表失败: ${data.error}`, 'error')
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      console.error('loadFiles timeout')
      showNotification(`加载文件列表超时，请重试`, 'error')
    } else {
      console.error('loadFiles error:', error)
      showNotification(`加载文件列表失败: ${error.message}`, 'error')
    }
  } finally {
    fm.loading = false
  }
}

const refreshFiles = (hostKey) => {
  const fm = fileManagers[hostKey]
  if (fm) {
    loadFiles(hostKey, fm.currentPath)
  }
}

const goParent = (hostKey) => {
  const fm = fileManagers[hostKey]
  if (!fm || fm.currentPath === '/') return

  const parentPath = fm.currentPath.split('/').slice(0, -1).join('/') || '/'
  loadFiles(hostKey, parentPath)
}

const handleFileDoubleClick = (hostKey, file) => {
  if (file.is_dir) {
    const fm = fileManagers[hostKey]
    const newPath = `${fm.currentPath.replace(/\/$/, '')}/${file.name}`
    loadFiles(hostKey, newPath)
  }
}

const downloadFile = async (hostKey, file) => {
  const fm = fileManagers[hostKey]
  if (!fm || !fm.sessionId) return

  const filePath = `${fm.currentPath.replace(/\/$/, '')}/${file.name}`

  try {
    const url = `${API_BASE}/file/download?session_id=${fm.sessionId}&path=${encodeURIComponent(filePath)}`

    // 创建隐藏的 a 标签直接下载，让浏览器处理下载进度
    const a = document.createElement('a')
    a.href = url
    a.download = file.name
    a.style.display = 'none'
    document.body.appendChild(a)
    a.click()

    // 延迟移除，确保下载已开始
    setTimeout(() => {
      document.body.removeChild(a)
    }, 100)

    // 不显示通知，让浏览器自己处理下载提示
  } catch (error) {
    console.error('Download error:', error)
    showNotification(`下载失败: ${error.message}`, 'error')
  }
}

const triggerUpload = (hostKey) => {
  const input = uploadInputs[hostKey]
  if (input) {
    input.click()
  }
}

const handleFileUpload = async (event, hostKey) => {
  const fm = fileManagers[hostKey]
  if (!fm || !fm.sessionId) return

  const file = event.target.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append('session_id', fm.sessionId)
  formData.append('path', fm.currentPath)
  formData.append('file', file)

  // 初始化上传进度
  fm.uploading = true
  fm.uploadProgress = 0
  fm.uploadFileName = file.name

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    // 监听上传进度
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percentComplete = Math.round((e.loaded / e.total) * 100)
        fm.uploadProgress = percentComplete
      }
    })

    // 监听完成
    xhr.addEventListener('load', async () => {
      try {
        const data = JSON.parse(xhr.responseText)

        if (data.status === 'success') {
          fm.uploadProgress = 100
          showNotification(`上传成功: ${file.name}`, 'success')

          // 立即隐藏进度条
          setTimeout(() => {
            fm.uploading = false
            fm.uploadProgress = 0
            fm.uploadFileName = ''
          }, 500)

          // 刷新文件列表（不阻塞进度条隐藏）
          loadFiles(hostKey, fm.currentPath).catch(err => {
            console.error('Refresh files error:', err)
          })
        } else {
          showNotification(`上传失败: ${data.error}`, 'error')
          fm.uploading = false
          fm.uploadProgress = 0
          fm.uploadFileName = ''
        }
      } catch (error) {
        showNotification(`上传失败: ${error.message}`, 'error')
        fm.uploading = false
        fm.uploadProgress = 0
        fm.uploadFileName = ''
      } finally {
        // 清空input
        event.target.value = ''
      }
      resolve()
    })

    // 监听错误
    xhr.addEventListener('error', () => {
      showNotification(`上传失败: 网络错误`, 'error')
      event.target.value = ''
      fm.uploading = false
      fm.uploadProgress = 0
      fm.uploadFileName = ''
      reject(new Error('网络错误'))
    })

    // 发送请求
    xhr.open('POST', `${API_BASE}/file/upload`)
    xhr.send(formData)
  })
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// Validate hosts
const validateHosts = async () => {
  const validHosts = getValidHosts()
  addTerminalLine('info', `[SSH] 验证 ${validHosts.length} 台主机连接...`)

  try {
    const response = await fetch(`${API_BASE}/validate-hosts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hosts: validHosts,
        username: config.username,
        password: config.password,
        port: config.port,
        type: 'ssh'
      })
    })

    const data = await response.json()
    validationResults.value = data.results

    // 为每个成功的主机创建唯一的标签（使用时间戳）
    const newHosts = data.results
      .filter(r => r.status === 'success')
      .map(r => {
        const timestamp = Date.now()
        const hostKey = `s${r.host}_${timestamp}`
        return { key: hostKey, host: r.host }
      })

    // 添加到 connectedHosts
    for (const { key, host } of newHosts) {
      connectedHosts.value.push(key)
      // 初始化终端
      if (!hostTerminals.value[key]) {
        hostTerminals.value[key] = []
      }
      // 建立SSH WebSocket连接
      await connectSSH(key, host, config.username, config.password, config.port)
    }

    // 设置最新连接的主机为激活标签
    if (newHosts.length > 0) {
      activeHostTab.value = newHosts[0].key
    }

    data.results.forEach(r => {
      const icon = r.status === 'success' ? '✅' : r.status === 'warning' ? '⚠️' : '❌'
      addTerminalLine(r.status === 'error' ? 'error' : 'info', `[SSH] ${icon} ${r.host}: ${r.message}`)
    })

    if (data.results.every(r => r.status === 'success')) {
      showNotification('[SSH] 所有主机连接成功', 'success')
    } else {
      showNotification('[SSH] 部分主机连接失败', 'warning')
    }
  } catch (error) {
    addTerminalLine('error', `[SSH] 验证失败: ${error.message}`)
    showNotification(`[SSH] 验证失败: ${error.message}`, 'error')
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

  // Output command to console
  console.log('='.repeat(80))
  console.log('FIO Test Command:')
  console.log(fioCommand)
  console.log('='.repeat(80))

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
  // Cleanup xterm instances
  Object.values(xtermInstances).forEach(({ term }) => {
    if (term) term.dispose()
  })
  disconnectWebSocket()
})

// Watch activeHostTab to fit terminal when switching
watch(activeHostTab, (newHostKey) => {
  if (newHostKey && xtermInstances[newHostKey]) {
    nextTick(() => {
      xtermInstances[newHostKey].fitAddon.fit()
    })
  }
})

// Initialize charts on mount
onMounted(() => {
  nextTick(() => {
    initCharts()
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
  height: 800px;
  max-height: 800px;
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
  border-radius: 8px;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: transparent;
  padding: 0;
  min-height: 0;
}

/* SSH Terminal specific styles */
.xterm-container {
  flex: 1;
  overflow: auto;
  background: #1e1e1e;
  border-radius: 8px;
  padding: 15px;
  min-height: 0;
}

/* File Manager Styles */
.file-manager-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  overflow: hidden;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  max-height: 100%;
  min-height: 0;
}

.file-manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 2px solid #e0e0e0;
  background: #f5f5f5;
}

.path-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.path-label {
  font-weight: 600;
  color: #666;
}

.path-value {
  color: #333;
  font-family: 'Consolas', monospace;
  background: #fff;
  padding: 4px 12px;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.file-actions {
  display: flex;
  gap: 10px;
}

/* Upload Progress */
.upload-progress {
  padding: 15px;
  background: #f9f9f9;
  border-bottom: 1px solid #e0e0e0;
}

.upload-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.upload-filename {
  color: #333;
  font-weight: 500;
}

.upload-percent {
  color: #6B5DD3;
  font-weight: 600;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6B5DD3, #8B7FE8);
  transition: width 0.3s ease;
  border-radius: 4px;
}

.file-list {
  flex: 1;
  overflow-y: scroll !important;  /* 强制显示滚动条 */
  overflow-x: hidden;
  padding: 10px;
  min-height: 0;
  max-height: 100%;
}

/* 确保滚动条可见 */
.file-list::-webkit-scrollbar {
  width: 10px;
}

.file-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.file-list::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.file-list::-webkit-scrollbar-thumb:hover {
  background: #555;
}

.file-item {
  display: grid;
  grid-template-columns: 40px 1fr 100px 60px;
  align-items: center;
  padding: 10px 15px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.file-item:hover {
  background: #f0f0f0;
}

.file-item.parent {
  background: #f8f8f8;
  border: 1px dashed #ddd;
}

.file-item.directory {
  font-weight: 500;
}

.file-icon {
  font-size: 20px;
  text-align: center;
}

.file-name {
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  color: #666;
  font-size: 12px;
  text-align: right;
}

.file-actions-cell {
  text-align: center;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.btn-icon:hover {
  background: #e0e0e0;
}

.file-loading,
.file-empty {
  text-align: center;
  padding: 40px;
  color: #999;
  font-size: 14px;
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
  display: flex;
  align-items: center;
  gap: 8px;
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

.tab-close {
  margin-left: auto;
  font-size: 18px;
  font-weight: bold;
  line-height: 1;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.tab-close:hover {
  opacity: 1;
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
