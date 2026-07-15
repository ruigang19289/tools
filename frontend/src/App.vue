<template>
  <div class="app">
    <router-view v-slot="{ Component, route }">
      <KeepAlive>
        <component :is="Component" :key="route.name || route.fullPath" />
      </KeepAlive>
    </router-view>
  </div>
</template>

<script setup>
import { KeepAlive } from 'vue'
</script>

<style scoped>
.app {
  min-height: 100vh;
}
</style>
