import { resolve } from 'node:path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'

/**
 * Layout: renderer mora em ./frontend/ (codigo legado da versao web,
 * reaproveitado como renderer Electron).
 *
 * - main:      ./electron/main/index.ts
 * - preload:   ./electron/preload/index.ts
 * - renderer:  ./frontend/  (entry: ./frontend/index.html → ./frontend/src/main.tsx)
 *
 * Outputs vao para ./out/{main,preload,renderer}.
 */
export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: {
      outDir: 'out/main',
      lib: {
        entry: resolve(__dirname, 'electron/main/index.ts'),
      },
    },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      outDir: 'out/preload',
      lib: {
        entry: resolve(__dirname, 'electron/preload/index.ts'),
      },
    },
  },
  renderer: {
    root: resolve(__dirname, 'frontend'),
    plugins: [react()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'frontend/src'),
      },
    },
    build: {
      outDir: resolve(__dirname, 'out/renderer'),
      rollupOptions: {
        input: resolve(__dirname, 'frontend/index.html'),
      },
    },
    server: {
      port: 5173,
    },
  },
})
