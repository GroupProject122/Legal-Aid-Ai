import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // Guarantees `src/index.ts` skips `app.listen()` (see the NODE_ENV guard
    // there); supertest drives the app in-process instead.
    env: { NODE_ENV: "test" },
  },
});
