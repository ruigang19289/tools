import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import fs from 'fs'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 6500,
    proxy: {
      '/api': {
        target: 'http://localhost:6000',
        changeOrigin: true
      },
      '/api/v1/perf/fio/ws': {
        target: 'ws://localhost:6000',
        ws: true
      },
      '/api/v1/network/iperf3/ws': {
        target: 'ws://localhost:6000',
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  },
  appType: 'spa'
})
