<template>
  <div class="ssh-credentials">
    <h2 v-if="title" class="section-title">{{ title }}</h2>

    <div class="form-group">
      <label>{{ hostLabel }}:</label>
      <input
        type="text"
        v-model="connection.host"
        :placeholder="hostPlaceholder"
        @input="$emit('update:connection', connection)"
      >
    </div>

    <div class="form-group">
      <label>SSH 端口:</label>
      <input
        type="text"
        v-model="connection.port"
        placeholder="22"
        @input="$emit('update:connection', connection)"
      >
    </div>

    <div class="form-group">
      <label>SSH 用户名:</label>
      <input
        type="text"
        v-model="connection.username"
        placeholder="root"
        @input="$emit('update:connection', connection)"
      >
    </div>

    <div class="form-group">
      <label>SSH 密码:</label>
      <input
        type="text"
        v-model="connection.password"
        placeholder="密码"
        @input="$emit('update:connection', connection)"
      >
    </div>
  </div>
</template>

<script setup>
import { watch } from 'vue'

const props = defineProps({
  connection: {
    type: Object,
    required: true
  },
  title: {
    type: String,
    default: 'SSH 认证'
  },
  hostLabel: {
    type: String,
    default: '主机地址'
  },
  hostPlaceholder: {
    type: String,
    default: '192.168.1.100'
  }
})

const emit = defineEmits(['update:connection'])

// 监听 connection 变化并触发更新
watch(() => props.connection, (newVal) => {
  emit('update:connection', newVal)
}, { deep: true })
</script>

<style scoped>
.ssh-credentials {
  /* 使用全局样式，这里只定义特殊样式 */
}
</style>
