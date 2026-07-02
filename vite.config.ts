import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'

import pkg from './package.json' with { type: 'json' }

// https://vite.dev/config/
export default defineConfig({
  // Deploy target sets the base path. Default suits the GitHub Pages subpath
  // (unimelbmdap.github.io/spotify-unpacked/); the Caddy/backend deploy serves
  // the SPA at the domain root, so its image builds with VITE_BASE=/.
  base: process.env.VITE_BASE || '/spotify-unpacked/',
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  plugins: [
    vue(),
    vueDevTools(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
