<template>
  <div class="header">
    <router-link to="/" class="back-btn">🏠</router-link>
    <h1>{{ title }}</h1>
    <span class="subtitle">{{ subtitle }}</span>
  </div>
</template>

<script setup>
defineProps({
  icon: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.header {
  background: white;
  padding: 15px 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  margin-bottom: 20px;
}

.back-btn {
  color: #6B5DD3;
  text-decoration: none;
  font-size: 24px;
  padding: 8px 12px;
  background: rgba(107, 93, 211, 0.1);
  border-radius: 8px;
  transition: all 0.3s;
}

.back-btn:hover {
  background: rgba(107, 93, 211, 0.2);
  transform: scale(1.1);
}

.header h1 {
  color: #6B5DD3;
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.subtitle {
  color: #6B5DD3;
  font-size: 14px;
  opacity: 0.8;
}
</style>
