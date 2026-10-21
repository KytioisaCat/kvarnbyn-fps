import { defineConfig } from 'vite';

// Deployas av .github/workflows/deploy.yml till https://kytioisacat.github.io/kvarnbyn-fps/v2/
// (v1 ligger kvar på roten). Lokalt/dev: base '/'.
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/kvarnbyn-fps/v2/' : '/',
  build: {
    target: 'es2022',
    sourcemap: true,
    chunkSizeWarningLimit: 2000,
  },
  server: { host: true },
}));
