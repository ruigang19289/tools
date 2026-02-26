/**
 * SSH 连接通用 Composable
 * 提供 SSH 连接的通用逻辑和状态管理
 */
import { ref, reactive, computed } from 'vue'

export function useSSHConnection(defaultPort = '22') {
  // SSH 连接配置
  const connection = reactive({
    host: '',
    port: defaultPort,
    username: '',
    password: ''
  })

  // 连接状态
  const isConnecting = ref(false)
  const isConnected = ref(false)
  const connectionError = ref('')

  // 表单验证
  const isFormValid = computed(() => {
    return connection.host.trim() &&
           connection.username.trim() &&
           connection.password
  })

  // 重置连接
  const resetConnection = () => {
    connection.host = ''
    connection.port = defaultPort
    connection.username = ''
    connection.password = ''
    isConnecting.value = false
    isConnected.value = false
    connectionError.value = ''
  }

  // 设置连接信息
  const setConnection = (host, username, password, port = defaultPort) => {
    connection.host = host
    connection.username = username
    connection.password = password
    connection.port = port
  }

  // 获取连接配置对象
  const getConnectionConfig = () => {
    return {
      host: connection.host,
      port: parseInt(connection.port),
      username: connection.username,
      password: connection.password
    }
  }

  return {
    connection,
    isConnecting,
    isConnected,
    connectionError,
    isFormValid,
    resetConnection,
    setConnection,
    getConnectionConfig
  }
}

/**
 * 主机列表管理 Composable
 * 用于管理多个主机的输入和验证
 */
export function useHostList(initialHosts = ['']) {
  const hosts = ref([...initialHosts])
  const validationResults = ref([])

  // 添加主机
  const addHost = () => {
    hosts.value.push('')
  }

  // 删除主机
  const removeHost = (index) => {
    if (hosts.value.length > 1) {
      hosts.value.splice(index, 1)
      validationResults.value.splice(index, 1)
    }
  }

  // 获取有效主机列表
  const getValidHosts = () => {
    return hosts.value.filter(host => host.trim())
  }

  // 清空验证结果
  const clearValidation = () => {
    validationResults.value = []
  }

  // 设置验证结果
  const setValidationResults = (results) => {
    validationResults.value = results
  }

  return {
    hosts,
    validationResults,
    addHost,
    removeHost,
    getValidHosts,
    clearValidation,
    setValidationResults
  }
}
