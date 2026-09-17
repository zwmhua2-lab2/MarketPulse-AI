import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Application requests stay same-origin and relative (`/api/...`). In development
      // they are forwarded to the local backend exactly as written — no rewrite strips
      // the `/api` prefix, because the backend already serves `/api/v1/...`.
      // A broad development CORS allow-list is deliberately not used as a workaround
      // (UI-V1-D01 §27, UI-F01 §13).
      "/api": { target: "http://127.0.0.1:8000" },
    },
  },
});
