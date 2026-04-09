import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
      '/explorer': 'http://localhost:8000',
      '/verify': 'http://localhost:8000',
      '/trace': 'http://localhost:8000',
      '/impact': 'http://localhost:8000',
      '/diff': 'http://localhost:8000',
      '/runs': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})
