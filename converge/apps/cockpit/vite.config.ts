import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 4173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:4174",
        changeOrigin: false,
      },
    },
  },
  preview: {
    port: 4173,
    strictPort: true,
  },
  build: {
    target: "es2022",
    sourcemap: true,
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: "react",
              test: /node_modules[\\/](?:react|react-dom|scheduler)[\\/]/,
              priority: 40,
            },
            {
              name: "lineage",
              test: /node_modules[\\/](?:@xyflow|d3-|zustand)[\\/]/,
              priority: 30,
            },
            {
              name: "motion",
              test: /node_modules[\\/](?:motion|motion-dom|motion-utils|framer-motion)[\\/]/,
              priority: 20,
            },
            {
              name: "icons",
              test: /node_modules[\\/]@phosphor-icons[\\/]/,
              priority: 10,
            },
          ],
        },
      },
    },
  },
});
