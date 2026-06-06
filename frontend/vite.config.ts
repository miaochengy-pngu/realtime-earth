import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import cesium from "vite-plugin-cesium";
import { fileURLToPath, URL } from "node:url";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiBase = env.VITE_API_BASE || "/api";
  const wsBase = env.VITE_WS_BASE || "/ws";
  return {
    plugins: [vue(), cesium()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    define: {
      __API_BASE__: JSON.stringify(apiBase),
      __WS_BASE__: JSON.stringify(wsBase),
    },
    server: {
      port: 5173,
      host: "0.0.0.0",
      proxy: {
        [apiBase]: {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
        [wsBase]: {
          target: "ws://localhost:8000",
          ws: true,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: true,
      chunkSizeWarningLimit: 1500, // Cesium is a large bundle
    },
  };
});
