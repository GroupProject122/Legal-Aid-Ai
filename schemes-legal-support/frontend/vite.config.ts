import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev server on :5173 (Vite default). The backend runs on :4000 — add a
// `server.proxy` entry here once the frontend starts calling the API.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
