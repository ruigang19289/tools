<template>
  <Transition name="slide">
    <div v-if="notification.show" :class="['notification-toast', notification.type]">
      {{ notification.message }}
    </div>
  </Transition>
</template>

<script setup>
defineProps({
  notification: {
    type: Object,
    required: true
  }
})
</script>

<style scoped>
.notification-toast {
  position: fixed;
  top: 80px;
  right: 20px;
  padding: 15px 25px;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 9999;
  max-width: 400px;
}

.notification-toast.success {
  background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
}

.notification-toast.error {
  background: linear-gradient(135deg, #f44336 0%, #da190b 100%);
}

.notification-toast.info {
  background: linear-gradient(135deg, #2196F3 0%, #0b7dda 100%);
}

.notification-toast.warning {
  background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
}

/* 过渡动画 */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from {
  transform: translateX(400px);
  opacity: 0;
}

.slide-leave-to {
  transform: translateX(400px);
  opacity: 0;
}
</style>
