<template>
  <div class="ansible-page">
    <PageHeader
      icon="📡"
      title="Ansible 管理平台"
    />

    <div class="main-content">
      <!-- 左侧：主机配置 -->
      <div class="left-panel">
        <div class="section">
          <h2 class="section-title">主机配置</h2>
          <div class="form-group">
            <label>主机列表 (每行一个IP或范围):</label>
            <textarea
              v-model="hostsText"
              rows="4"
              placeholder="192.168.1.1&#10;192.168.1.2&#10;192.168.1.10-20"
            ></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>用户名:</label>
              <input type="text" v-model="username" placeholder="root">
            </div>
            <div class="form-group">
              <label>端口:</label>
              <input type="number" v-model="port" placeholder="22">
            </div>
          </div>
          <div class="form-group">
            <label>密码:</label>
            <input type="password" v-model="password" placeholder="******">
          </div>
          <button class="btn btn-primary btn-full" @click="validateHosts" :disabled="!canValidate">
            验证连接
          </button>
        </div>

        <!-- 已验证主机列表 -->
        <div class="section" v-if="validatedHosts.length > 0">
          <h2 class="section-title">已验证主机 ({{ validatedHosts.length }})</h2>
          <div class="host-list">
            <div
              v-for="host in validatedHosts"
              :key="host.ip"
              :class="['host-item', { selected: selectedHosts.includes(host.ip) }]"
              @click="toggleHost(host.ip)"
            >
              <span class="host-ip">{{ host.ip }}</span>
              <span :class="['host-status', host.status]">{{ host.status === 'success' ? '✓' : '✗' }}</span>
            </div>
          </div>
          <div class="btn-group">
            <button class="btn btn-secondary btn-compact" @click="selectAll">全选</button>
            <button class="btn btn-secondary btn-compact" @click="clearSelection">清空</button>
          </div>
        </div>
      </div>

      <!-- 右侧：功能面板 -->
      <div class="right-panel">
        <!-- 功能标签页 -->
        <div class="tabs">
          <button
            :class="['tab-btn', { active: activeTab === 'command' }]"
            @click="activeTab = 'command'"
          >
            命令执行
          </button>
          <button
            :class="['tab-btn', { active: activeTab === 'file' }]"
            @click="activeTab = 'file'"
          >
            文件分发
          </button>
          <button
            :class="['tab-btn', { active: activeTab === 'playbook' }]"
            @click="activeTab = 'playbook'"
          >
            Playbook
          </button>
          <button
            :class="['tab-btn', { active: activeTab === 'modules' }]"
            @click="activeTab = 'modules'"
          >
            模块
          </button>
        </div>

        <!-- 命令执行面板 -->
        <div v-if="activeTab === 'command'" class="tab-content">
          <div class="section">
            <h2 class="section-title">批量命令执行</h2>
            <div class="form-group">
              <label>选择模块:</label>
              <select v-model="commandModule" class="form-select">
                <option value="shell">Shell 命令</option>
                <option value="command">Command 命令</option>
                <option value="ping">Ping 测试</option>
                <option value="setup">收集主机信息</option>
              </select>
            </div>
            <div class="form-group">
              <label>命令:</label>
              <textarea
                v-model="command"
                rows="4"
                placeholder="输入要执行的命令..."
              ></textarea>
            </div>
            <button
              class="btn btn-primary"
              @click="executeCommand"
              :disabled="!canExecute || executing"
            >
              {{ executing ? '执行中...' : '执行命令' }}
            </button>
          </div>
        </div>

        <!-- 文件分发面板 -->
        <div v-if="activeTab === 'file'" class="tab-content">
          <div class="section">
            <h2 class="section-title">文件分发</h2>
            <div class="form-group">
              <label>分发方式:</label>
              <select v-model="fileAction" class="form-select">
                <option value="push">推送文件</option>
                <option value="pull">拉取文件</option>
              </select>
            </div>
            <div class="form-group">
              <label>源路径:</label>
              <input type="text" v-model="sourcePath" :placeholder="fileAction === 'push' ? '/path/to/local/file' : '/path/on/remote'">
            </div>
            <div class="form-group">
              <label>目标路径:</label>
              <input type="text" v-model="destPath" placeholder="/path/on/remote">
            </div>
            <div class="form-group">
              <label>
                <input type="checkbox" v-model="fileBackup"> 目标文件备份
              </label>
            </div>
            <button
              class="btn btn-primary"
              @click="transferFile"
              :disabled="!canTransfer || transferring"
            >
              {{ transferring ? '传输中...' : '开始传输' }}
            </button>
          </div>
        </div>

        <!-- Playbook面板 -->
        <div v-if="activeTab === 'playbook'" class="tab-content">
          <div class="section">
            <h2 class="section-title">Playbook 执行</h2>
            <div class="form-group">
              <label>Playbook 内容 (YAML):</label>
              <textarea
                v-model="playbookContent"
                rows="15"
                placeholder="- hosts: all&#10;  tasks:&#10;    - name: Ensure nginx is installed&#10;      yum:&#10;        name: nginx&#10;        state: present"
                class="code-editor"
              ></textarea>
            </div>
            <div class="btn-group">
              <button
                class="btn btn-primary"
                @click="runPlaybook"
                :disabled="!canRunPlaybook || runningPlaybook"
              >
                {{ runningPlaybook ? '执行中...' : '执行 Playbook' }}
              </button>
              <button class="btn btn-secondary" @click="validatePlaybook">
                验证语法
              </button>
            </div>
          </div>
        </div>

        <!-- 模块面板 -->
        <div v-if="activeTab === 'modules'" class="tab-content">
          <div class="section">
            <h2 class="section-title">常用模块</h2>
            <div class="modules-grid">
              <button
                v-for="mod in commonModules"
                :key="mod.name"
                class="module-btn"
                @click="useModule(mod)"
              >
                <span class="module-name">{{ mod.name }}</span>
                <span class="module-desc">{{ mod.desc }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 执行结果 -->
        <div class="section terminal-section">
          <div class="terminal-header">
            <h2 class="section-title">执行结果</h2>
            <div class="terminal-controls">
              <button class="btn btn-compact" @click="clearOutput">清空</button>
              <button class="btn btn-compact" @click="downloadOutput">下载</button>
            </div>
          </div>
          <div class="terminal-window" ref="terminalWindow">
            <div v-for="(line, idx) in output" :key="idx" class="log-line">
              <span class="time">{{ line.time }}</span>
              <span :class="['message', line.type]">{{ line.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'

const API_BASE = '/api/v1/system/ansible'

// Form data
const hostsText = ref('')
const username = ref('root')
const port = ref(22)
const password = ref('')

// State
const validatedHosts = ref([])
const selectedHosts = ref([])
const activeTab = ref('command')
const executing = ref(false)
const transferring = ref(false)
const runningPlaybook = ref(false)
const output = ref([])
const terminalWindow = ref(null)

// Command tab
const commandModule = ref('shell')
const command = ref('')

// File transfer tab
const fileAction = ref('push')
const sourcePath = ref('')
const destPath = ref('')
const fileBackup = ref(true)

// Playbook tab
const playbookContent = ref('')

// Common modules
const commonModules = [
  { name: 'shell', desc: '执行Shell命令' },
  { name: 'command', desc: '执行命令' },
  { name: 'yum', desc: '安装软件包' },
  { name: 'copy', desc: '复制文件' },
  { name: 'file', desc: '文件属性管理' },
  { name: 'service', desc: '服务管理' },
  { name: 'systemd', desc: '系统服务管理' },
  { name: 'selinux', desc: 'SELinux管理' },
  { name: 'firewalld', desc: '防火墙管理' },
  { name: 'template', desc: '模板文件' },
  { name: 'sync', desc: '目录同步' },
  { name: 'cron', desc: '定时任务' },
]

// Computed
const canValidate = computed(() => {
  return hostsText.value.trim() && username.value.trim() && password.value
})

const canExecute = computed(() => {
  // ping 和 setup 模块不需要输入命令
  if (commandModule.value === 'ping' || commandModule.value === 'setup') {
    return selectedHosts.value.length > 0
  }
  return selectedHosts.value.length > 0 && command.value.trim()
})

const canTransfer = computed(() => {
  return selectedHosts.value.length > 0 && sourcePath.value.trim() && destPath.value.trim()
})

const canRunPlaybook = computed(() => {
  return selectedHosts.value.length > 0 && playbookContent.value.trim()
})

// Methods
const parseIPRange = (input) => {
  const ips = []
  const lines = input.split('\n').map(l => l.trim()).filter(l => l)
  
  for (const line of lines) {
    if (line.includes('/')) {
      const match = line.match(/^(\d+\.\d+\.\d+\.)(\d+)\/(\d+)$/)
      if (match) {
        const prefix = match[1]
        const base = parseInt(match[2])
        const bits = parseInt(match[3])
        const count = Math.pow(2, 32 - bits)
        for (let i = 0; i < count; i++) {
          ips.push(prefix + (base + i))
        }
      }
      continue
    }
    
    const rangeMatch = line.match(/^(\d+\.\d+\.\d+\.)(\d+)-(\d+)$/)
    if (rangeMatch) {
      const prefix = rangeMatch[1]
      const start = parseInt(rangeMatch[2])
      const end = parseInt(rangeMatch[3])
      for (let i = start; i <= end; i++) {
        ips.push(prefix + i)
      }
      continue
    }
    
    ips.push(line)
  }
  
  return ips
}

const addOutput = (message, type = 'info') => {
  const now = new Date()
  const time = now.toLocaleTimeString()
  output.value.push({ time, message, type })
  nextTick(() => {
    if (terminalWindow.value) {
      terminalWindow.value.scrollTop = terminalWindow.value.scrollHeight
    }
  })
}

const validateHosts = async () => {
  const ips = parseIPRange(hostsText.value)
  addOutput(`开始验证 ${ips.length} 个主机...`, 'info')
  
  validatedHosts.value = []
  
  for (const ip of ips) {
    try {
      const response = await fetch(`${API_BASE}/validate-hosts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hosts: [{
            ip,
            username: username.value,
            password: password.value,
            port: port.value
          }]
        })
      })
      const data = await response.json()
      
      validatedHosts.value.push({
        ip,
        status: data.results?.[0]?.status === 'success' ? 'success' : 'error'
      })
      
      addOutput(`${ip}: ${data.results?.[0]?.status === 'success' ? '连接成功' : data.results?.[0]?.message || '连接失败'}`, 
        data.results?.[0]?.status === 'success' ? 'success' : 'error')
    } catch (e) {
      validatedHosts.value.push({ ip, status: 'error' })
      addOutput(`${ip}: 验证失败 - ${e.message}`, 'error')
    }
  }
  
  // 验证完成后默认全选所有主机
  selectAll()
}

const toggleHost = (ip) => {
  const idx = selectedHosts.value.indexOf(ip)
  if (idx > -1) {
    selectedHosts.value.splice(idx, 1)
  } else {
    selectedHosts.value.push(ip)
  }
}

const selectAll = () => {
  selectedHosts.value = validatedHosts.value.map(h => h.ip)
}

const clearSelection = () => {
  selectedHosts.value = []
}

const executeCommand = async () => {
  executing.value = true
  addOutput(`[${commandModule.value}] 在 ${selectedHosts.value.length} 台主机执行命令...`, 'info')
  addOutput(`命令: ${command.value}`, 'info')
  
  try {
    const hostsWithCreds = selectedHosts.value.map(ip => ({
      ip,
      username: username.value,
      password: password.value,
      port: port.value
    }))
    
    const response = await fetch(`${API_BASE}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hosts: hostsWithCreds,
        module: commandModule.value,
        command: command.value
      })
    })
    const data = await response.json()
    
    if (data.results) {
      for (const r of data.results) {
        addOutput(`\n=== ${r.ip} ===`, 'info')
        addOutput(r.output || r.error || '无输出', r.success ? 'success' : 'error')
      }
    }
    
    addOutput('\n命令执行完成', 'success')
  } catch (e) {
    addOutput(`执行失败: ${e.message}`, 'error')
  } finally {
    executing.value = false
  }
}

const transferFile = async () => {
  transferring.value = true
  addOutput(`开始文件传输到 ${selectedHosts.value.length} 台主机...`, 'info')
  
  try {
    const hostsWithCreds = selectedHosts.value.map(ip => ({
      ip,
      username: username.value,
      password: password.value,
      port: port.value
    }))
    
    const response = await fetch(`${API_BASE}/file-transfer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hosts: hostsWithCreds,
        action: fileAction.value,
        source: sourcePath.value,
        dest: destPath.value,
        backup: fileBackup.value
      })
    })
    const data = await response.json()
    
    if (data.results) {
      for (const r of data.results) {
        addOutput(`${r.ip}: ${r.success ? '传输成功' : r.error}`, r.success ? 'success' : 'error')
      }
    }
  } catch (e) {
    addOutput(`传输失败: ${e.message}`, 'error')
  } finally {
    transferring.value = false
  }
}

const runPlaybook = async () => {
  runningPlaybook.value = true
  addOutput('开始执行 Playbook...', 'info')
  
  try {
    const hostsWithCreds = selectedHosts.value.map(ip => ({
      ip,
      username: username.value,
      password: password.value,
      port: port.value
    }))
    
    const response = await fetch(`${API_BASE}/playbook`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hosts: hostsWithCreds,
        playbook: playbookContent.value
      })
    })
    const data = await response.json()
    
    addOutput(data.output || 'Playbook 执行完成', 'success')
  } catch (e) {
    addOutput(`执行失败: ${e.message}`, 'error')
  } finally {
    runningPlaybook.value = false
  }
}

const validatePlaybook = async () => {
  addOutput('验证 Playbook 语法...', 'info')
  // 简化的语法验证
  try {
    // 基本 YAML 格式检查
    const lines = playbookContent.value.split('\n')
    let hasHosts = false
    let hasTasks = false
    
    for (const line of lines) {
      if (line.includes('hosts:')) hasHosts = true
      if (line.includes('tasks:')) hasTasks = true
    }
    
    if (hasHosts && hasTasks) {
      addOutput('Playbook 语法验证通过', 'success')
    } else {
      addOutput('Playbook 格式可能不完整，请检查 hosts 和 tasks', 'error')
    }
  } catch (e) {
    addOutput(`验证失败: ${e.message}`, 'error')
  }
}

const useModule = (mod) => {
  activeTab.value = 'command'
  commandModule.value = mod.name
  
  const templates = {
    shell: '# 输入要执行的 Shell 命令\n',
    command: '# 输入要执行的命令\n',
    yum: '# yum: name=httpd state=present\n',
    copy: '# copy: src=/path/to/file dest=/path/to/dest\n',
    file: '# file: path=/path/to/file mode=0755 state=file\n',
    service: '# service: name=httpd state=started enabled=yes\n',
    systemd: '# systemd: name=httpd state=started enabled=yes\n',
    selinux: '# selinux: state=disabled\n',
    firewalld: '# firewalld: service=httpd permanent=yes state=enabled\n',
    template: '# template: src=template.j2 dest=/path/to/file\n',
    sync: '# synchronize: src=/path/to/dest dest=/path/on/remote/\n',
    cron: '# cron: name="job" minute="0" job="/path/to/job"\n'
  }
  
  command.value = templates[mod.name] || ''
}

const clearOutput = () => {
  output.value = []
}

const downloadOutput = () => {
  const content = output.value.map(l => `[${l.time}] ${l.message}`).join('\n')
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ansible_output_${new Date().toISOString().replace(/[:.]/g, '-')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.ansible-page {
  min-height: 100vh;
  padding: 20px;
  background: linear-gradient(135deg, #2D5A27 0%, #4A7C43 50%, #6B9B37 100%);
}

.main-content {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  margin-top: 20px;
}

.left-panel, .right-panel {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #333;
}

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
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: #4A7C43;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.host-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #eee;
  border-radius: 6px;
  margin-bottom: 10px;
}

.host-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid #eee;
}

.host-item:last-child {
  border-bottom: none;
}

.host-item.selected {
  background: #e8f5e9;
}

.host-status.success {
  color: #4CAF50;
}

.host-status.error {
  color: #f44336;
}

.tabs {
  display: flex;
  border-bottom: 2px solid #eee;
  margin-bottom: 20px;
}

.tab-btn {
  padding: 10px 20px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}

.tab-btn.active {
  color: #4A7C43;
  border-bottom-color: #4A7C43;
}

.code-editor {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  background: #f5f5f5;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.module-btn {
  padding: 12px;
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  text-align: left;
}

.module-btn:hover {
  background: #e8f5e9;
  border-color: #4A7C43;
}

.module-name {
  display: block;
  font-weight: 600;
  color: #333;
}

.module-desc {
  display: block;
  font-size: 11px;
  color: #999;
}

.terminal-section {
  margin-top: 20px;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.terminal-controls {
  display: flex;
  gap: 10px;
}

.terminal-window {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 15px;
  height: 300px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.log-line {
  padding: 2px 0;
}

.log-line .time {
  color: #666;
  margin-right: 8px;
}

.log-line .message {
  color: #fff;
}

.log-line .message.success {
  color: #4CAF50;
}

.log-line .message.error {
  color: #f44336;
}

.btn-group {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}
</style>
