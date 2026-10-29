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
      // Python FastAPI backend: every API the app uses, including Schemes.
      '/api': 'http://localhost:8000'
    }
  }
});
