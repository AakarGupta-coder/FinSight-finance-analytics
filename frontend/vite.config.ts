import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // Local development: forward API calls to the FastAPI backend.
      '/api': { target: process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
  build: { sourcemap: false, chunkSizeWarningLimit: 900 },
})
