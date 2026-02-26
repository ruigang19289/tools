/**
 * 通知提示 Composable
 * 提供统一的通知消息管理
 */
import { reactive } from 'vue'

export function useNotification() {
  const notification = reactive({
    show: false,
    message: '',
    type: 'info' // info, success, error, warning
  })

  const showNotification = (message, type = 'info', duration = 3000) => {
    notification.message = message
    notification.type = type
    notification.show = true

    if (duration > 0) {
      setTimeout(() => {
        notification.show = false
      }, duration)
    }
  }

  const hideNotification = () => {
    notification.show = false
  }

  const showSuccess = (message, duration = 3000) => {
    showNotification(message, 'success', duration)
  }

  const showError = (message, duration = 3000) => {
    showNotification(message, 'error', duration)
  }

  const showWarning = (message, duration = 3000) => {
    showNotification(message, 'warning', duration)
  }

  const showInfo = (message, duration = 3000) => {
    showNotification(message, 'info', duration)
  }

  return {
    notification,
    showNotification,
    hideNotification,
    showSuccess,
    showError,
    showWarning,
    showInfo
  }
}

/**
 * 终端输出 Composable
 * 用于管理终端输出行
 */
export function useTerminal() {
  const lines = reactive([])

  const addLine = (text, type = 'info') => {
    lines.push({
      text,
      type,
      timestamp: new Date().toLocaleTimeString()
    })
  }

  const addSuccess = (text) => addLine(text, 'success')
  const addError = (text) => addLine(text, 'error')
  const addWarning = (text) => addLine(text, 'warning')
  const addInfo = (text) => addLine(text, 'info')

  const clearLines = () => {
    lines.splice(0, lines.length)
  }

  return {
    lines,
    addLine,
    addSuccess,
    addError,
    addWarning,
    addInfo,
    clearLines
  }
}
