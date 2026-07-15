<template>
  <div class="cosbench-page">
    <PageHeader
      icon="🔧"
      title="CosBench 配置文件生成"
    />

    <!-- Main Content -->
    <div class="main-content">
      <!-- Row 1: Controller Configuration -->
      <div class="controller-section">
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">
              Controller 配置
            </h2>
            <!-- <button class="btn btn-primary" @click="generateConfig" :disabled="!canGenerate">
              生成文件
            </button> -->
          </div>
          <div class="form-grid">
            <div class="form-group narrow">
              <label>Driver 节点 IP (每行一个):</label>
              <textarea v-model="config.ipListText" rows="3" placeholder="172.16.151.128
172.16.151.129
172.16.151.130"></textarea>
            </div>
            <div></div>
            <div></div>
            <div class="form-group">
              <label>每 IP Driver:</label>
              <input type="number" v-model="config.driversPerIp" min="1" max="10">
            </div>
            <div class="form-group">
              <label>起始端口:</label>
              <input type="number" v-model="config.startPort" min="1024">
            </div>
            <div class="form-group">
              <label>步长:</label>
              <input type="number" v-model="config.portStep" min="1" value="100">
            </div>
          </div>
          <!-- <div class="info-bar">
            <span>总 Driver: <strong>{{ totalDrivers }}</strong></span>
            <span>端口序列: <code>{{ portSequencePreview }}</code></span>
          </div> -->
        </div>
      </div>

      <!-- Row 2: Workload Configuration -->
      <div class="workload-section">
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">
              Workload 配置
            </h2>
            <!-- <button class="btn btn-primary" @click="generateConfig" :disabled="!canGenerate">
              生成文件
            </button> -->
          </div>

          <div class="form-grid">
            <div class="form-group endpoint-wide">
              <label>Endpoint (每行一个):</label>
              <textarea v-model="s3.endpointsText" rows="3" placeholder="http://192.168.1.1:8060
http://192.168.1.2:8060
http://192.168.1.3:8060"></textarea>
            </div>
            <div></div>
            <div class="form-group">
              <label>Access Key:</label>
              <input type="text" v-model="s3.accessKey" placeholder="Access Key">
            </div>
            <div class="form-group">
              <label>Secret Key:</label>
              <input type="text" v-model="s3.secretKey" placeholder="Secret Key">
            </div>
            <div></div>
            <div class="form-group">
              <label>测试名称:</label>
              <input type="text" v-model="workload.name" placeholder="s3-benchmark">
            </div>
            <div class="form-group">
              <label>操作类型:</label>
              <select v-model="workload.operationType">
                <option value="write">Write (写)</option>
                <option value="read">Read (读)</option>
                <option value="mixed">Mixed (混合读写)</option>
              </select>
            </div>
            <div class="form-group" v-if="workload.operationType === 'mixed'" style="display: flex; align-items: flex-end;">
              <label style="margin-right: 8px;">读/写比例:</label>
              <input type="number" v-model="workload.readRatio" min="0" max="100" placeholder="50" style="width: 60px;">
              <span style="margin: 0 4px;">/</span>
              <span>{{ 100 - workload.readRatio }}</span>
            </div>
            <div class="form-group" v-else></div>
            <div class="form-group">
              <label>Driver 数:</label>
              <input type="number" v-model="workload.numDrivers" min="1">
            </div>
            <div class="form-group">
              <label>Worker/Driver:</label>
              <input type="number" v-model="workload.workersPerDriver" min="1">
            </div>
            <div class="form-group">
              <label>总操作数:</label>
              <input type="number" v-model="workload.totalOps" min="1">
            </div>
            <div class="form-group">
              <label>对象大小:</label>
              <div class="input-group">
                <input type="number" v-model="workload.objectSizeMb" min="1">
                <select v-model="workload.sizeUnit">
                  <option value="KB">KB</option>
                  <option value="MB">MB</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>Bucket 前缀:</label>
              <input type="text" v-model="workload.bucketPrefix" placeholder="test-">
            </div>
            <div class="form-group">
              <label>对象前缀:</label>
              <input type="text" v-model="workload.objectPrefix" placeholder="obj-">
            </div>
          </div>
        </div>
      </div>

      <!-- Preview Column (spans 2 rows) -->
      <div class="preview-column">
        <!-- Output Tabs -->
        <div class="output-section">
          <div class="output-tabs">
            <button :class="['tab', { active: outputTab === 'xml' }]" @click="outputTab = 'xml'">
              Workload.xml
            </button>
            <button :class="['tab', { active: outputTab === 'controller' }]" @click="outputTab = 'controller'">
              Controller.conf
            </button>
            <div class="tab-spacer"></div>
            <button v-if="generated" class="tab action" @click="copyCurrent">复制</button>
            <button v-if="generated" class="tab action" @click="downloadCurrent">下载</button>
            <button class="tab action primary" @click="generateConfig" :disabled="!canGenerate">生成配置</button>
          </div>

          <!-- Code Preview -->
          <div class="code-area">
            <pre v-if="generated">{{ currentOutput }}</pre>
            <div v-else class="empty">配置完成后点击"生成配置"...</div>
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
import { ref, reactive, computed } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'

const API_BASE = `/api/v1/perf/cosbench`

// Output tab
const outputTab = ref('xml')

// Controller Configuration
const config = reactive({
  ipListText: '',
  driversPerIp: 2,
  startPort: 18088,
  portStep: 100
})

// S3 Configuration
const s3 = reactive({
  accessKey: '',
  secretKey: '',
  endpointsText: '',
  pathStyleAccess: true,
  serverSideEncryption: false
})

// Workload Configuration
const workload = reactive({
  name: 's3-benchmark',
  description: 'S3 基准测试',
  numDrivers: 1,
  workersPerDriver: 100,
  totalOps: 100000,
  operationType: 'write',
  readRatio: 50,
  objectSizeMb: 4,
  sizeUnit: 'KB',
  bucketPrefix: 'test-',
  objectPrefix: 'obj-'
})

// Generated data
const generated = ref(false)
const controllerConf = ref('')
const workloadXml = ref('')

// Notification
const notification = reactive({
  show: false,
  message: '',
  type: 'info'
})

// Computed
const totalDrivers = computed(() => {
  const ips = getIpList()
  return ips.length * config.driversPerIp
})

const portSequencePreview = computed(() => {
  const ports = []
  for (let i = 0; i < config.driversPerIp; i++) {
    ports.push(config.startPort + i * config.portStep)
  }
  return ports.join(', ')
})

const canGenerate = computed(() => {
  const ips = getIpList()
  return ips.length > 0 && s3.accessKey && s3.secretKey
})

const currentOutput = computed(() => {
  return outputTab.value === 'controller' ? controllerConf.value : workloadXml.value
})

// Helper functions
const getIpList = () => {
  return config.ipListText.split('\n').map(ip => ip.trim()).filter(ip => ip)
}

const showNotification = (message, type = 'info') => {
  notification.message = message
  notification.type = type
  notification.show = true
  setTimeout(() => {
    notification.show = false
  }, 3000)
}

// Generate configuration
const generateConfig = async () => {
  const ips = getIpList()
  const endpoints = s3.endpointsText.split('\n').map(ep => ep.trim()).filter(ep => ep)

  try {
    const response = await fetch(`${API_BASE}/generate-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ip_list: ips,
        drivers_per_ip: config.driversPerIp,
        start_port: config.startPort,
        port_step: config.portStep,
        workload_name: workload.name,
        workload_description: workload.description,
        endpoints: endpoints,
        access_key: s3.accessKey,
        secret_key: s3.secretKey,
        num_drivers: workload.numDrivers,
        workers_per_driver: workload.workersPerDriver,
        total_ops: workload.totalOps,
        operation_type: workload.operationType,
        read_ratio: workload.operationType === 'read' ? 100 : (workload.operationType === 'mixed' ? workload.readRatio : 0),
        write_ratio: workload.operationType === 'write' ? 100 : (workload.operationType === 'mixed' ? 100 - workload.readRatio : 0),
        object_size_mb: workload.objectSizeMb,
        size_unit: workload.sizeUnit,
        bucket_prefix: workload.bucketPrefix,
        object_prefix: workload.objectPrefix,
        path_style_access: s3.pathStyleAccess,
        server_side_encryption: s3.serverSideEncryption,
      })
    })

    const data = await response.json()

    if (data.status === 'success') {
      controllerConf.value = data.controller_conf
      workloadXml.value = data.workload_xml
      generated.value = true
      outputTab.value = 'xml'
      showNotification('配置生成成功', 'success')
    } else {
      showNotification(`生成失败: ${data.error}`, 'error')
    }
  } catch (error) {
    showNotification(`生成失败: ${error.message}`, 'error')
  }
}

// Download
const downloadCurrent = () => {
  const content = currentOutput.value
  let filename
  
  if (outputTab.value === 'controller') {
    filename = 'controller.conf'
  } else {
    // 生成符合格式的文件名：S3-4k-write-1driver
    const sizeStr = `${workload.objectSizeMb}${workload.sizeUnit.toLowerCase().replace('mb', 'm').replace('kb', 'k')}`
    const typeStr = workload.operationType
    const driverStr = `${workload.numDrivers}driver`
    
    filename = `S3-${sizeStr}-${typeStr}-${driverStr}.xml`
  }

  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
  showNotification('文件已下载', 'success')
}

// Copy
const copyCurrent = async () => {
  const content = currentOutput.value
  if (!content) {
    showNotification('没有可复制的内容', 'warning')
    return
  }

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(content)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = content
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    showNotification('已复制到剪贴板', 'success')
  } catch (error) {
    showNotification('复制失败，请手动选择内容复制', 'error')
  }
}
</script>

<style scoped>
.cosbench-page { min-height: 100vh; padding: 20px; background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 50%, #9B8FF8 100%); position: relative; }
.cosbench-page::before { content: ''; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: repeating-linear-gradient(45deg, transparent, transparent 35px, rgba(255,255,255,0.05) 35px, rgba(255,255,255,0.05) 70px); pointer-events: none; z-index: 0; }
.cosbench-page > * { position: relative; z-index: 1; }

.main-content {
  display: grid;
  grid-template-columns: 640px 1fr;
  grid-template-rows: auto auto;
  gap: 20px;
}

.controller-section {
  grid-column: 1;
  grid-row: 1;
}

.workload-section {
  grid-column: 1;
  grid-row: 2;
}

.preview-column {
  grid-column: 2;
  grid-row: 1 / 3;
  display: flex;
  flex-direction: column;
  gap: 20px;
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
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #6B5DD3;
}

.section-header .section-title {
  margin-bottom: 0;
}

.section-title .icon {
  font-size: 18px;
}

.subsection-title {
  font-size: 15px;
  font-weight: 600;
  color: #6B5DD3;
  margin: 20px 0 12px 0;
  padding-bottom: 8px;
}

.subsection-title:first-of-type {
  margin-top: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 15px;
}

.form-group {
  margin-bottom: 0;
}

.form-group.full {
  grid-column: span 3;
}

.form-group.endpoint-wide {
  grid-column: span 2;
}

.form-group label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  font-family: monospace;
}

.form-group textarea {
  resize: vertical;
  min-height: 50px;
}

.input-group {
  display: flex;
  gap: 5px;
}

.input-group input {
  flex: 1;
}

.input-group select {
  width: 70px;
}

.info-bar {
  display: flex;
  gap: 20px;
  margin-top: 12px;
  margin-left: -20px;
  margin-right: -20px;
  padding: 10px 20px;
  background: #f0f4ff;
  border-radius: 0;
  font-size: 12px;
  color: #666;
}

.info-bar strong {
  color: #6B5DD3;
}

.info-bar code {
  background: #e0e0e0;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.checkbox-row {
  display: flex;
  gap: 20px;
  margin-top: 12px;
  font-size: 13px;
}

.checkbox-row label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.checkbox-row input[type="checkbox"] {
  width: 16px;
  height: 16px;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:disabled {
  background: #f0eef8 !important;
  color: #9b8ff8 !important;
  border: 1px solid #e0ddf0 !important;
  cursor: not-allowed;
}

.btn-large {
  padding: 15px 30px;
  font-size: 16px;
}

/* Preview Column */
.summary-box {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr;
  gap: 15px;
  padding: 15px 20px;
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 100%);
  border-radius: 12px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-item.full {
  grid-column: span 1;
}

.summary-item .label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.8);
}

.summary-item .value {
  font-size: 24px;
  font-weight: 700;
  color: white;
}

.summary-item .link {
  font-size: 12px;
  color: white;
  text-decoration: underline;
}

.output-section {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 15px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 715px; /* 调整到 715px */
}

.output-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 15px;
}

.tab {
  padding: 8px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.tab:hover {
  border-color: #6B5DD3;
}

.tab.active {
  border-color: #6B5DD3;
  background: #6B5DD3;
  color: white;
}

.tab.action {
  border-style: dashed;
}

.tab.action.primary {
  border-style: solid;
  border-color: #6B5DD3;
  background: #6B5DD3;
  color: white;
  font-weight: 600;
}

.tab.action.primary:hover {
  background: #5a4dc2;
  border-color: #5a4dc2;
}

.tab.action.primary:disabled {
  background: #f0eef8;
  color: #9b8ff8;
  border-color: #e0ddf0;
  cursor: not-allowed;
}

.tab-spacer {
  flex: 1;
}

.code-area {
  flex: 1;
  background: #1e1e1e;
  border-radius: 8px;
  padding: 15px;
  overflow: auto;
  max-height: 635px; /* 调整到 635px */
  min-height: 300px; /* 最小高度保持美观 */
}

.code-area pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
}

.empty {
  color: #666;
  text-align: center;
  padding: 40px;
}

/* Notification */
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

.notification.success {
  background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
}

.notification.error {
  background: linear-gradient(135deg, #f44336 0%, #da190b 100%);
}

@media (max-width: 1024px) {
  .main-content {
    grid-template-columns: 1fr;
  }

  .summary-box {
    grid-template-columns: 1fr 1fr;
  }

  .summary-item.full {
    grid-column: span 2;
  }
}
</style>
