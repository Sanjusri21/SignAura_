import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss()
  ],
  server: {
    port: 5174,
    host: true,
    // The backend, avatar service and datasets are not part of the frontend. Without this, every file an
    // extraction or conversion writes under them (index.json, .npz, caches) reloads the open page.
    watch: {
      ignored: ['**/Backend/**', '**/SignAvatars/**', '**/SignMotionDB/**']
    }
  }
});
