<template>
  <div class="postgres-page">
    <PageHeader
      icon="🗄️"
      title="数据库连接工具"
    />

    <!-- Main Content -->
    <div class="main-content">
      <!-- Left Panel: Connection -->
      <div class="left-panel">
        <!-- Database Type Selection -->
        <div class="section">
          <h2 class="section-title">数据库类型</h2>
          <div class="db-type-selector">
            <div
              v-for="type in dbTypes"
              :key="type.value"
              :class="['db-type-card', { active: selectedType === type.value, disabled: type.disabled }]"
              @click="!type.disabled && selectType(type.value)"
            >
              <span class="type-icon">{{ type.icon }}</span>
              <span class="type-name">{{ type.name }}</span>
              <span v-if="type.disabled" class="disabled-badge">不可用</span>
            </div>
          </div>
        </div>

        <!-- Connection Form -->
        <div class="section">
          <h2 class="section-title">连接配置</h2>

          <div class="form-group">
            <label>远程主机:</label>
            <input type="text" v-model="connection.host" placeholder="192.168.1.1">
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>端口:</label>
              <input type="number" v-model="connection.port" :placeholder="currentTypeConfig.defaultPort">
            </div>
            <div class="form-group">
              <label>用户名:</label>
              <input type="text" v-model="connection.username" :placeholder="currentTypeConfig.defaultUser">
            </div>
          </div>

          <div class="form-group">
            <label>密码:</label>
            <input type="password" v-model="connection.password" placeholder="******">
          </div>

          <div v-if="selectedType === 'fdb'" class="form-group">
            <label>配置文件:</label>
            <input type="text" v-model="connection.configFile" placeholder="/etc/foundationdb/fdb.cluster">
          </div>

          <div v-if="selectedType !== 'fdb'" class="form-group">
            <label>数据库:</label>
            <input type="text" v-model="connection.database" :placeholder="currentTypeConfig.defaultDatabase">
          </div>

          <div class="btn-group">
            <button
              class="btn btn-primary btn-full"
              @click="connectDB"
              :disabled="!canConnect || isConnected || isConnecting"
            >
              {{ isConnecting ? '连接中...' : (isConnected ? '已连接' : '连接') }}
            </button>
            <button
              v-if="isConnected"
              class="btn btn-danger btn-full"
              @click="disconnectDB"
            >
              断开连接
            </button>
          </div>
        </div>
      </div>

      <!-- Right Panel: Info & Query -->
      <div class="right-panel">
        <!-- Database Objects Table -->
        <div v-if="isConnected" class="section info-section">
          <h2 class="table-title">数据库对象列表 ({{ currentDatabase }})</h2>
          <div class="info-table-wrapper">
            <table class="info-table">
              <thead>
                <tr>
                  <th>Schema</th>
                  <th>名称</th>
                  <th>类型</th>
                  <th>所有者</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="table in tables" :key="table.name" @click="selectTable(table.name)" :class="{ active: selectedTable === table.name }">
                  <td>{{ table.schema }}</td>
                  <td class="table-name-cell">{{ table.name }}</td>
                  <td>
                    <span class="type-badge" :class="table.type">{{ table.type }}</span>
                  </td>
                  <td>{{ table.owner }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Table Structure -->
        <div v-if="selectedTable && tableStructure" class="section table-structure-section">
          <h2 class="table-title">表结构 - {{ selectedTable }} ({{ tableStructure.columns ? tableStructure.columns.length : 0 }} 列)</h2>
          <div class="structure-table-wrapper">
            <table class="structure-table">
              <thead>
                <tr>
                  <th>列名</th>
                  <th>数据类型</th>
                  <th>可空</th>
                  <th>默认值</th>
                  <th>备注</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(col, index) in tableStructure.columns" :key="index">
                  <td class="column-name-cell">{{ col.column_name }}</td>
                  <td>{{ col.data_type }}</td>
                  <td>
                    <span class="nullable-badge" :class="col.is_nullable === 'YES' ? 'yes' : 'no'">
                      {{ col.is_nullable === 'YES' ? '是' : '否' }}
                    </span>
                  </td>
                  <td>
                    <span v-if="col.column_default" class="default-value">{{ col.column_default }}</span>
                    <span v-else class="null-value">-</span>
                  </td>
                  <td>{{ col.description || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- All Tables List -->
        <div v-if="selectedTable && tableData" class="section tables-data-section">
          <h2 class="table-title">
            表数据 - {{ selectedTable }}
            <span class="data-count">({{ tableData.total_rows }} 行)</span>
          </h2>
          <div class="table-data-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="col in tableData.columns" :key="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in tableData.data" :key="idx">
                  <td v-for="col in tableData.columns" :key="col">
                    <span v-if="row[col] === null" class="null-value">NULL</span>
                    <span v-else>{{ row[col] }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="tableData.total_rows > tableData.limit" class="pagination-info">
            显示 {{ tableData.offset + 1 }} - {{ Math.min(tableData.offset + tableData.limit, tableData.total_rows) }} / {{ tableData.total_rows }} 行
          </div>
        </div>

        <!-- Table Relationships -->
        <div v-if="selectedTable && tableStructure" class="section relationships-section">
          <h2 class="table-title">表关系 - {{ selectedTable }}</h2>

          <div v-if="tableStructure.foreign_keys.length === 0 && tableStructure.referenced_by.length === 0" class="empty-state">
            <span class="empty-icon">🔗</span>
            <p>该表没有关联关系</p>
          </div>

          <div v-else class="relationships-container">
            <!-- Outgoing relationships -->
            <div v-if="tableStructure.foreign_keys.length > 0" class="relationship-group">
              <h3 class="relationship-title">引用其他表 (Foreign Keys) - {{ tableStructure.foreign_keys.length }} 个</h3>
              <div class="relationship-list">
                <div v-for="fk in tableStructure.foreign_keys" :key="fk.constraint_name" class="relationship-item outgoing">
                  <div class="relationship-arrow">→</div>
                  <div class="relationship-content">
                    <div class="relationship-main">
                      <span class="current-table">{{ selectedTable }}</span>
                      <span class="column-name">.{{ fk.column }}</span>
                      <span class="arrow-text">引用</span>
                      <span class="referenced-table">{{ fk.referenced_table }}</span>
                      <span class="column-name">.{{ fk.referenced_column }}</span>
                    </div>
                    <div class="constraint-name">{{ fk.constraint_name }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Incoming relationships -->
            <div v-if="tableStructure.referenced_by.length > 0" class="relationship-group">
              <h3 class="relationship-title">被其他表引用 (Referenced By) - {{ tableStructure.referenced_by.length }} 个</h3>
              <div class="relationship-list">
                <div v-for="ref in tableStructure.referenced_by" :key="ref.constraint_name + ref.referencing_table" class="relationship-item incoming" :class="{ potential: ref.type === 'potential' }">
                  <div class="relationship-arrow">←</div>
                  <div class="relationship-content">
                    <div class="relationship-main">
                      <span class="referenced-table">{{ ref.referencing_table }}</span>
                      <span class="column-name">.{{ ref.referencing_column }}</span>
                      <span class="arrow-text">引用</span>
                      <span class="current-table">{{ selectedTable }}</span>
                      <span class="column-name">.{{ ref.column }}</span>
                      <span v-if="ref.type === 'potential'" class="potential-badge">潜在关联</span>
                    </div>
                    <div class="constraint-name">{{ ref.constraint_name }}</div>
                  </div>
                </div>
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
import { ref, reactive, computed } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'

// Database Types Configuration (updated)
const dbTypes = [
  { value: 'mysql', name: 'MySQL', icon: '🐬', defaultPort: '3306', defaultUser: 'root', defaultDatabase: 'mysql', queryPlaceholder: 'SELECT * FROM table_name LIMIT 100', disabled: true },
  { value: 'postgresql', name: 'PostgreSQL', icon: '🐘', defaultPort: '5432', defaultUser: 'postgres', defaultDatabase: 'postgres', queryPlaceholder: 'SELECT * FROM table_name LIMIT 100', disabled: false },
  { value: 'fdb', name: 'FoundationDB', icon: '🔷', defaultPort: '4500', defaultUser: 'admin', defaultDatabase: '', queryPlaceholder: 'get key_prefix', disabled: true }
]

const selectedType = ref('postgresql')
const currentTypeConfig = computed(() => dbTypes.find(t => t.value === selectedType.value) || dbTypes[1])

// Connection
const connection = reactive({
  host: '',
  port: 5432,
  username: '',
  password: '',
  database: 'postgres',
  configFile: '/etc/foundationdb/fdb.cluster'
})

// State
const isConnected = ref(false)
const isConnecting = ref(false)
const connectionId = ref('')
const tables = ref([])
const currentDatabase = ref('')
const selectedTable = ref('')
const tableStructure = ref(null)
const tableData = ref(null)

// Query
const query = ref('')
const queryResult = ref(null)

// Notification
const notification = reactive({
  show: false,
  message: '',
  type: 'info'
})

// Computed
const canConnect = computed(() => {
  if (selectedType.value === 'fdb') {
    return connection.host.trim() && connection.username.trim()
  }
  return connection.host.trim() && connection.username.trim() && connection.database.trim()
})

const canQuery = computed(() => {
  return isConnected.value && query.value.trim()
})

// Methods
const showNotification = (message, type = 'info') => {
  notification.message = message
  notification.type = type
  notification.show = true
  setTimeout(() => {
    notification.show = false
  }, 3000)
}

const selectType = (type) => {
  if (isConnected.value) {
    if (!confirm('切换数据库类型将断开当前连接，确定继续吗？')) {
      return
    }
    disconnectDB()
  }

  selectedType.value = type
  const config = dbTypes.find(t => t.value === type)
  connection.port = parseInt(config.defaultPort)
  connection.username = config.defaultUser
  connection.database = config.defaultDatabase
}

// Connect to database
const connectDB = async () => {
  if (!connection.host || !connection.username) {
    showNotification('请填写完整连接信息', 'error')
    return
  }

  isConnecting.value = true

  try {
    const apiPath = selectedType.value === 'fdb' ? '/api/v1/system/fdb' : `/api/v1/system/${selectedType.value}`
    const requestBody = {
      host: connection.host,
      port: connection.port,
      username: connection.username,
      password: connection.password
    }

    // FDB使用配置文件，其他数据库使用database参数
    if (selectedType.value === 'fdb') {
      requestBody.config_file = connection.configFile
    } else {
      requestBody.database = connection.database
    }

    const response = await fetch(`${apiPath}/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    })

    const data = await response.json()

    if (data.status === 'success') {
      isConnected.value = true
      connectionId.value = data.connection_id || ''
      tables.value = data.tables || []
      currentDatabase.value = data.database || connection.database
      showNotification(`已连接到 ${currentTypeConfig.value.name}`, 'success')
    } else {
      showNotification(`连接失败: ${data.error}`, 'error')
    }
  } catch (error) {
    showNotification(`连接错误: ${error.message}`, 'error')
  } finally {
    isConnecting.value = false
  }
}

// Disconnect from database
const disconnectDB = async () => {
  if (connectionId.value) {
    try {
      const apiPath = selectedType.value === 'fdb' ? '/api/v1/system/fdb' : `/api/v1/system/${selectedType.value}`
      await fetch(`${apiPath}/disconnect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ connection_id: connectionId.value })
      })
    } catch (error) {
      console.error('Disconnect error:', error)
    }
  }

  isConnected.value = false
  connectionId.value = ''
  tables.value = []
  currentDatabase.value = ''
  selectedTable.value = ''
  tableStructure.value = null
  tableData.value = null
  queryResult.value = null
  showNotification('已断开连接', 'info')
}

// Select table
const selectTable = async (tableName) => {
  selectedTable.value = tableName

  try {
    const apiPath = selectedType.value === 'fdb' ? '/api/v1/system/fdb' : `/api/v1/system/${selectedType.value}`

    // 并行请求表结构和表数据
    const [structureResponse, dataResponse] = await Promise.all([
      fetch(`${apiPath}/table-structure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connection_id: connectionId.value,
          table_name: tableName
        })
      }),
      fetch(`${apiPath}/table-data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connection_id: connectionId.value,
          table_name: tableName,
          limit: 100,
          offset: 0
        })
      })
    ])

    const structureData = await structureResponse.json()
    const dataData = await dataResponse.json()

    if (structureData.status === 'success') {
      tableStructure.value = structureData
    } else {
      showNotification(`加载表结构失败: ${structureData.error}`, 'error')
    }

    if (dataData.status === 'success') {
      tableData.value = dataData
      showNotification(`已加载表: ${tableName}`, 'success')
    } else {
      showNotification(`加载表数据失败: ${dataData.error}`, 'error')
    }
  } catch (error) {
    showNotification(`加载表错误: ${error.message}`, 'error')
  }
}

// Execute query
const executeQuery = async () => {
  if (!canQuery.value) return

  try {
    const apiPath = selectedType.value === 'fdb' ? '/api/v1/system/fdb' : `/api/v1/system/${selectedType.value}`
    const response = await fetch(`${apiPath}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connection_id: connectionId.value,
        database: currentDatabase.value,
        query: query.value
      })
    })

    const data = await response.json()

    if (data.status === 'success') {
      queryResult.value = {
        columns: data.columns || [],
        data: data.data || [],
        total_rows: data.total_rows || 0,
        message: `查询成功，返回 ${data.total_rows || 0} 行`
      }
      showNotification('查询执行成功', 'success')
    } else {
      queryResult.value = {
        error: data.error || '查询失败'
      }
      showNotification('查询失败', 'error')
    }
  } catch (error) {
    queryResult.value = {
      error: error.message
    }
    showNotification(`查询错误: ${error.message}`, 'error')
  }
}

// Clear query
const clearQuery = () => {
  query.value = ''
  queryResult.value = null
}

// Load sample query
const loadSampleQuery = () => {
  if (selectedType.value === 'fdb') {
    query.value = 'get my_key'
  } else {
    query.value = 'SELECT * FROM information_schema.tables LIMIT 10'
  }
}
</script>

<style scoped>
.postgres-page {
  min-height: 100vh;
  padding: 20px;
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 50%, #9B8FF8 100%);
  position: relative;
  overflow-x: hidden;
}

.postgres-page > * {
  position: relative;
  z-index: 1;
}

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

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* Database Type Selector */
.db-type-selector {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.db-type-card {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  padding: 12px 15px;
  background: rgba(255, 255, 255, 0.7);
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.db-type-card:hover:not(.disabled) {
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-2px);
}

.db-type-card.active {
  background: white;
  border-color: #6B5DD3;
  box-shadow: 0 4px 12px rgba(107, 93, 211, 0.3);
}

.db-type-card.disabled {
  background: rgba(200, 200, 200, 0.3);
  cursor: not-allowed;
  opacity: 0.5;
}

.db-type-card.disabled .type-icon,
.db-type-card.disabled .type-name {
  color: #999;
}

.disabled-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 10px;
  padding: 2px 6px;
  background: #f44336;
  color: white;
  border-radius: 3px;
  font-weight: 600;
}

.type-icon {
  font-size: 32px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.type-name {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

/* Info Section */
.info-section {
  height: 350px;
  display: flex;
  flex-direction: column;
}

.info-table-wrapper {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.info-table {
  width: 100%;
  border-collapse: collapse;
}

.info-table thead {
  position: sticky;
  top: 0;
  background: #f8f9fa;
  z-index: 1;
}

.info-table th {
  padding: 10px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
  border-bottom: 2px solid #e0e0e0;
}

.info-table td {
  padding: 10px;
  border-bottom: 1px solid #e0e0e0;
  font-size: 13px;
}

.info-table tbody tr {
  cursor: pointer;
  transition: background 0.2s;
}

.info-table tbody tr:hover {
  background: #f8f9fa;
}

.info-table tbody tr.active {
  background: #e7f3ff;
}

.status-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.status-badge.success {
  background: #e8f5e9;
  color: #2e7d32;
}

.type-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.type-badge.table {
  background: #e3f2fd;
  color: #1976d2;
}

.type-badge.view {
  background: #f3e5f5;
  color: #7b1fa2;
}

.type-badge.sequence {
  background: #fff3e0;
  color: #f57c00;
}

.section {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.table-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 15px;
  border-bottom: none;
  padding-bottom: 0;
}


.db-badge {
  font-size: 12px;
  padding: 4px 10px;
  background: #6B5DD3;
  color: white;
  border-radius: 20px;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.btn-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Database List */
.db-list {
  max-height: 200px;
  overflow-y: auto;
}

.db-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.db-item:hover {
  background: #f0f4ff;
}

.db-item.active {
  background: #6B5DD3;
  color: white;
}

.db-icon {
  font-size: 16px;
}

.db-name {
  font-size: 13px;
}

/* Table List */
.table-list {
  max-height: 250px;
  overflow-y: auto;
}

.table-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.table-item:hover {
  background: #f0f4ff;
}

.table-item.active {
  background: #6B5DD3;
  color: white;
}

.table-icon {
  font-size: 14px;
}

.table-name {
  flex: 1;
  font-size: 13px;
}

.table-rows {
  font-size: 11px;
  opacity: 0.7;
}

/* Query Section */
.query-section {
  flex-shrink: 0;
}

.query-box textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  resize: vertical;
  min-height: 120px;
}

.query-actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.query-info {
  margin-top: 10px;
  padding: 8px 12px;
  background: #e8f5e9;
  border-radius: 6px;
  font-size: 13px;
  color: #4CAF50;
}

/* Results Section */
.results-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.results-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.results-meta {
  display: flex;
  gap: 20px;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
  margin-bottom: 10px;
}

.results-table-wrapper {
  flex: 1;
  overflow: auto;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.results-table th,
.results-table td {
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  text-align: left;
  white-space: nowrap;
}

.results-table th {
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 100%);
  color: white;
  position: sticky;
  top: 0;
}

.results-table tr:nth-child(even) {
  background: #f9f9f9;
}

.empty-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #999;
}

.empty-icon,
.error-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.error-state {
  color: #f44336;
}

/* Structure */
.table-structures {
  max-height: 300px;
  overflow-y: auto;
}

.structure-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.structure-tabs .tab {
  padding: 8px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.structure-tabs .tab.active {
  border-color: #6B5DD3;
  background: #6B5DD3;
  color: white;
}

.structure-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.structure-table th,
.structure-table td {
  padding: 8px;
  border: 1px solid #e0e0e0;
}

.structure-table th {
  background: #f5f5f5;
}

.structure-table code {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.default {
  color: #999;
  font-size: 11px;
}

.index-item {
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 6px;
  margin-bottom: 8px;
}

.index-name {
  font-weight: 600;
  margin-right: 10px;
}

.index-def {
  font-size: 11px;
  color: #666;
}

.empty-hint {
  color: #999;
  font-size: 13px;
  text-align: center;
  padding: 20px;
}

/* Table name clickable */
.table-name-cell {
  cursor: pointer;
  color: #6B5DD3;
  font-weight: 500;
}

.table-name-cell:hover {
  text-decoration: underline;
}

.info-table tbody tr.active {
  background: #e7f3ff;
}

/* Tables List Section */
.table-structure-section {
  height: 300px;
  display: flex;
  flex-direction: column;
}

.structure-table-wrapper {
  overflow: auto;
  flex: 1;
  min-height: 0;
}

.structure-table {
  width: 100%;
  border-collapse: collapse;
}

.structure-table thead {
  position: sticky;
  top: 0;
  background: #f8f9fa;
  z-index: 1;
}

.structure-table th {
  padding: 10px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
  border-bottom: 2px solid #e0e0e0;
}

.structure-table td {
  padding: 10px;
  border-bottom: 1px solid #e0e0e0;
  font-size: 13px;
}

.column-name-cell {
  font-weight: 600;
  color: #6B5DD3;
}

.nullable-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.nullable-badge.yes {
  background: #fff3e0;
  color: #f57c00;
}

.nullable-badge.no {
  background: #e8f5e9;
  color: #2e7d32;
}

.default-value {
  font-family: monospace;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}

.tables-data-section {
  height: 450px;
  display: flex;
  flex-direction: column;
}

.table-data-wrapper {
  overflow: auto;
  flex: 1;
  min-height: 0;
  width: 1250px;
  border-radius: 6px;
  background: white;
}

.data-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.data-table th,
.data-table td {
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  text-align: left;
  white-space: nowrap;
}

.data-table th {
  background: linear-gradient(135deg, #6B5DD3 0%, #8B7FE8 100%);
  color: white;
  position: sticky;
  top: 0;
  z-index: 1;
  font-weight: 600;
}

.data-table tbody tr:nth-child(even) {
  background: #f9f9f9;
}

.data-table tbody tr:hover {
  background: #f0f4ff;
}

.null-value {
  color: #999;
  font-style: italic;
}

.data-count {
  font-size: 13px;
  color: #666;
  font-weight: normal;
  margin-left: 8px;
}

.pagination-info {
  margin-top: 10px;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
  text-align: center;
  flex-shrink: 0;
}

/* Relationships Section */
.relationships-section {
  height: 450px;
  display: flex;
  flex-direction: column;
}

.relationships-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.relationship-group {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
}

.relationship-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.relationship-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.relationship-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: white;
  border-radius: 6px;
  border-left: 4px solid #6B5DD3;
}

.relationship-item.outgoing {
  border-left-color: #2196F3;
}

.relationship-item.incoming {
  border-left-color: #4CAF50;
}

.relationship-item.potential {
  border-left-color: #FF9800;
  border-left-style: dashed;
}

.potential-badge {
  display: inline-block;
  padding: 2px 6px;
  background: #fff3e0;
  color: #f57c00;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  margin-left: 8px;
}

.relationship-arrow {
  font-size: 20px;
  font-weight: bold;
  color: #6B5DD3;
  line-height: 1;
}

.relationship-item.outgoing .relationship-arrow {
  color: #2196F3;
}

.relationship-item.incoming .relationship-arrow {
  color: #4CAF50;
}

.relationship-content {
  flex: 1;
}

.relationship-main {
  font-size: 13px;
  margin-bottom: 4px;
}

.current-table {
  font-weight: 600;
  color: #6B5DD3;
}

.referenced-table {
  font-weight: 600;
  color: #333;
}

.column-name {
  color: #666;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.arrow-text {
  color: #999;
  font-size: 12px;
  margin: 0 6px;
}

.constraint-name {
  font-size: 11px;
  color: #999;
  font-family: 'Courier New', monospace;
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
}
</style>
