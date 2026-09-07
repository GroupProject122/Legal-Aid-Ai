import "dotenv/config";
import cors from "cors";
import express, { type NextFunction, type Request, type Response } from "express";

import { healthRouter } from "./routes/health";
import { matchRouter } from "./routes/match";
import { schemesRouter } from "./routes/schemes";

export const app = express();
const PORT = Number(process.env.PORT ?? 4000);

app.use(cors());
app.use(express.json());

app.use("/health", healthRouter);
app.use("/match", matchRouter);
app.use("/schemes", schemesRouter);

app.get("/", (_req, res) => {
  res.json({ message: "Schemes & Legal Support API" });
});

// Fallback error handler — keeps malformed-JSON and unexpected errors from
// leaking a stack trace to the client.
app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
  if (err && typeof err === "object" && "type" in err && err.type === "entity.parse.failed") {
    return res.status(400).json({ error: "Malformed JSON body" });
  }
  console.error("[unhandled error]", err);
  return res.status(500).json({ error: "Internal server error" });
});

// Bind a port for `npm run dev` / `npm start`, but not under the test runner,
// which imports `app` and drives it in-process via supertest.
if (process.env.NODE_ENV !== "test") {
  app.listen(PORT, () => {
    console.log(`[backend] listening on http://localhost:${PORT}`);
  });
}
