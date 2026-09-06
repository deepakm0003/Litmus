import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';

/**
 * Two build targets from one source:
 *   npm run build          -> normal dist/ output for hosting
 *   SINGLE=1 npm run build -> everything inlined into one dist/index.html,
 *                             which is what gets published as an Artifact
 *                             (that sandbox serves a single file and blocks
 *                             separate asset requests).
 */
export default defineConfig({
  plugins: [react(), ...(process.env.SINGLE ? [viteSingleFile()] : [])],
  // `npm run dev` serves the UI on 5173 but the API lives on 8000. Proxy the
  // API paths across so the console talks to the real backend in development
  // exactly as it does when the backend serves the built bundle.
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    cssCodeSplit: false,
    assetsInlineLimit: 100000000,
  },
});
