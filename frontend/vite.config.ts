import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendHost = process.env.BACKEND_HOST ?? 'localhost';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': `http://${backendHost}:8000`,
      '/ws': {
        target: `ws://${backendHost}:8000`,
        ws: true,
      },
    },
  },
})
