import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base so the built site works at the CloudFront/S3 root.
export default defineConfig({
  base: "./",
  plugins: [react()],
});
