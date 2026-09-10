import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vite 开发与代理配置：/api 代理到本地后端
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // 静态资源（抓包文件 / 初始代码 / PDF 文档）也转发到后端
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
