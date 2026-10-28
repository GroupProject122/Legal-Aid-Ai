import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    // `npm run dev` serves the app on http://localhost:4000. strictPort: fail with an error if
    // 4000 is taken, rather than silently moving to another port.
    port: 4000,
    strictPort: true,
    proxy: {
      // Python FastAPI backend (legal RAG).
      '/api': 'http://localhost:8000',
      // Node schemes backend (Schemes & Legal Support), on 4001 so it never clashes with this
      // dev server on 4000. The `/schemes-api` prefix is stripped before forwarding, so the
      // browser calls `/schemes-api/match` and the backend sees `/match`.
      '/schemes-api': {
        target: 'http://localhost:4001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/schemes-api/, '')
      }
    }
  }
});
