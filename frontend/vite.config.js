import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vite 开发与代理配置：/api 代理到本地后端
export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      output: {
        // 手动切分第三方库，避免公共依赖（vue / markdown-it / highlight.js）
        // 被重复打进多个页面 chunk。
        //
        // 说明：vendor-pdf 只在真正渲染 PDF 时才下载（见 LabDetailView.vue 的
        // defineAsyncComponent），所以体积警告阈值放宽到 800 kB；
        // 其余 chunk 都远小于它，超限就说明又混进了不该有的东西。
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          const p = id.replace(/\\/g, '/')
          if (p.includes('/pdfjs-dist/') || p.includes('/vue-pdf-embed/')) return 'vendor-pdf'
          if (p.includes('/highlight.js/')) return 'vendor-highlight'
          if (p.includes('/markdown-it/')) return 'vendor-markdown'
          if (p.includes('/vue/') || p.includes('/vue-router/') || p.includes('/@vue/')) return 'vendor-vue'
          return 'vendor'
        },
      },
    },
    chunkSizeWarningLimit: 800,
  },
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
