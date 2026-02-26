<template>
  <div v-if="visible" :class="['notification', type]">
    {{ message }}
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  message: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'info', // info, success, error, warning
    validator: (value) => ['info', 'success', 'error', 'warning'].includes(value)
  },
  duration: {
    type: Number,
    default: 3000
  }
})

const visible = ref(false)
let timer = null

watch(() => props.message, (newMessage) => {
  if (newMessage) {
    visible.value = true
    if (timer) clearTimeout(timer)
    if (props.duration > 0) {
      timer = setTimeout(() => {
        visible.value = false
      }, props.duration)
    }
  }
})

defineExpose({
  show: () => { visible.value = true },
  hide: () => { visible.value = false }
})
</script>

<style scoped>
.notification {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 15px 25px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 9999;
  animation: slideIn 0.3s ease-out;
  max-width: 400px;
  font-size: 14px;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.notification.info {
  background: #3498db;
  color: white;
}

.notification.success {
  background: #2ecc71;
  color: white;
}

.notification.error {
  background: #e74c3c;
  color: white;
}

.notification.warning {
  background: #f39c12;
  color: white;
}
</style>
