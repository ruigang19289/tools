<template>
  <div class="host-list-manager">
    <div class="hosts-header">
      <span>{{ title }}</span>
      <button class="btn-small" @click="addHost">+</button>
    </div>

    <div class="host-list">
      <div v-for="(host, index) in hosts" :key="index" class="host-item">
        <input
          type="text"
          v-model="hosts[index]"
          :placeholder="placeholder"
          @input="$emit('update:hosts', hosts)"
        >
        <button
          v-if="hosts.length > 1"
          class="btn-remove"
          @click="removeHost(index)"
        >
          ×
        </button>
      </div>
    </div>

    <!-- 验证结果显示 -->
    <div v-if="validationResults && validationResults.length > 0" class="validation-summary">
      <span class="badge success" v-if="validationResults.every(r => r.status === 'success')">
        ✅ 全部连接成功
      </span>
      <span class="badge warning" v-else-if="validationResults.some(r => r.status === 'success')">
        ⚠️ 部分成功 ({{ validationResults.filter(r => r.status === 'success').length }}/{{ hosts.length }})
      </span>
      <span class="badge error" v-else>
        ❌ 连接失败
      </span>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  hosts: {
    type: Array,
    required: true
  },
  validationResults: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: '主机列表'
  },
  placeholder: {
    type: String,
    default: '192.168.1.100'
  }
})

const emit = defineEmits(['update:hosts', 'add', 'remove'])

const addHost = () => {
  props.hosts.push('')
  emit('update:hosts', props.hosts)
  emit('add')
}

const removeHost = (index) => {
  if (props.hosts.length > 1) {
    props.hosts.splice(index, 1)
    emit('update:hosts', props.hosts)
    emit('remove', index)
  }
}
</script>

<style scoped>
.host-list-manager {
  /* 使用全局样式 */
}

.hosts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-weight: 600;
  color: #333;
}

.host-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.host-item {
  display: flex;
  gap: 8px;
  align-items: center;
}

.host-item input {
  flex: 1;
}

.btn-remove {
  width: 28px;
  height: 28px;
  padding: 0;
  background: #f44336;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-remove:hover {
  background: #da190b;
  transform: scale(1.1);
}

.validation-summary {
  margin-top: 10px;
}
</style>
