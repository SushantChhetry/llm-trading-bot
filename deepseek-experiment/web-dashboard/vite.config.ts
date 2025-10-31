import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

/**
 * Vite Configuration
 * 
 * NOTE: The `server.proxy` configuration ONLY applies to the development server.
 * Production builds are static files and don't use this proxy.
 * 
 * In production (Vercel):
 * - Uses vercel.json rewrites to proxy /api/* requests to Railway
 * - Frontend code uses environment variable VITE_API_URL or relative paths
 * 
 * In development:
 * - Local: Uses localhost:8001 (via Vite proxy)
 * - Docker: Uses service name 'api:8001' (Docker Compose networking)
 */
const getApiProxyTarget = (): string => {
  // Explicit override via environment variable
  if (process.env.VITE_API_PROXY_TARGET) {
    return process.env.VITE_API_PROXY_TARGET
  }
  // Docker environment (set by docker-compose.dev.yml)
  if (process.env.DOCKER_ENV === 'true') {
    return 'http://api:8001'
  }
  // Default: local development outside Docker
  return 'http://localhost:8001'
}

const getWsProxyTarget = (): string => {
  // Explicit override via environment variable
  if (process.env.VITE_WS_PROXY_TARGET) {
    return process.env.VITE_WS_PROXY_TARGET
  }
  // Docker environment
  if (process.env.DOCKER_ENV === 'true') {
    return 'ws://api:8002'
  }
  // Default: local development outside Docker
  return 'ws://localhost:8002'
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // This server config only applies to `npm run dev` (development server)
  // It has NO effect on production builds (static files)
  server: {
    port: 3000,
    host: '0.0.0.0', // Allow access from outside container
    proxy: {
      '/api': {
        target: getApiProxyTarget(),
        changeOrigin: true,
        secure: false, // Allow self-signed certificates in dev
      },
      '/ws': {
        target: getWsProxyTarget(),
        ws: true,
        secure: false,
      },
    },
  },
})
