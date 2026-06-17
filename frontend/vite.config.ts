import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // O .env fica na raiz do repositório (compartilhado com o backend Django).
  envDir: '..',
  server: {
    port: 3000,
    open: true,
  },
});
