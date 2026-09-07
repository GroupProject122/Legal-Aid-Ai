import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Python FastAPI backend (legal RAG).
      '/api': 'http://localhost:8000',
      // Node schemes backend (Schemes & Legal Support). The `/schemes-api`
      // prefix is stripped before forwarding, so the browser calls
      // `/schemes-api/match` and the backend sees `/match`.
      '/schemes-api': {
        target: 'http://localhost:4000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/schemes-api/, '')
      }
    }
  }
});
