import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // In development, Vite serves the app and forwards API calls to FastAPI.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
