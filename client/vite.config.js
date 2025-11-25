import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        // Defines 'index.html' as the main entry point
        main: resolve(__dirname, 'index.html'),
        // Adds 'odds.html' as a second entry point
        odds: resolve(__dirname, 'odds.html'),
      },
    },
  },
});