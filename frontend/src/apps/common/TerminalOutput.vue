<template>
  <div class="terminal-output">
    <div v-if="title" class="terminal-header">
      <span class="terminal-title">{{ title }}</span>
      <div v-if="stats" class="terminal-stats">
        <slot name="stats">
          <span v-if="stats.success !== undefined">成功: {{ stats.success }}</span>
          <span v-if="stats.failed !== undefined">失败: {{ stats.failed }}</span>
          <span v-if="stats.timeout !== undefined">超时: {{ stats.timeout }}</span>
        </slot>
      </div>
      <button v-if="clearable" class="btn-clear" @click="$emit('clear')">清空</button>
    </div>

    <div class="terminal-window" ref="terminalWindow">
      <div
        v-for="(line, index) in lines"
        :key="index"
        :class="['terminal-line', line.type]"
      >
        <span v-if="showTimestamp" class="timestamp">{{ line.timestamp }}</span>
        <span class="line-content">{{ line.text }}</span>
      </div>

      <div v-if="lines.length === 0" class="terminal-empty">
        {{ emptyText }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  lines: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: ''
  },
  stats: {
    type: Object,
    default: null
  },
  clearable: {
    type: Boolean,
    default: false
  },
  showTimestamp: {
    type: Boolean,
    default: false
  },
  emptyText: {
    type: String,
    default: '暂无输出...'
  },
  autoScroll: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['clear'])

const terminalWindow = ref(null)

// 自动滚动到底部
watch(() => props.lines.length, () => {
  if (props.autoScroll) {
    nextTick(() => {
      if (terminalWindow.value) {
        terminalWindow.value.scrollTop = terminalWindow.value.scrollHeight
      }
    })
  }
})
</script>

<style scoped>
.terminal-output {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.terminal-header {
  background: #2c3e50;
  color: white;
  padding: 10px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.terminal-title {
  font-weight: 600;
  font-size: 14px;
}

.terminal-stats {
  display: flex;
  gap: 15px;
  font-size: 12px;
  opacity: 0.9;
}

.btn-clear {
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-clear:hover {
  background: rgba(255, 255, 255, 0.3);
}

.terminal-window {
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 13px;
  padding: 15px;
  height: 400px;
  overflow-y: auto;
}

.terminal-line {
  padding: 2px 0;
  line-height: 1.5;
}

.terminal-line .timestamp {
  color: #888;
  margin-right: 8px;
}

.terminal-line.success {
  color: #4CAF50;
}

.terminal-line.error {
  color: #f44336;
}

.terminal-line.warning {
  color: #ff9800;
}

.terminal-line.info {
  color: #2196F3;
}

.terminal-empty {
  color: #666;
  text-align: center;
  padding: 50px 20px;
  font-style: italic;
}

.terminal-window::-webkit-scrollbar {
  width: 8px;
}

.terminal-window::-webkit-scrollbar-track {
  background: #2c3e50;
}

.terminal-window::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

.terminal-window::-webkit-scrollbar-thumb:hover {
  background: #777;
}
</style>
