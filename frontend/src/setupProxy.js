// Proxy do servidor de desenvolvimento (npm start). Em produção quem faz esse papel é o Nginx (deploy/nginx.conf).
const { createProxyMiddleware } = require('http-proxy-middleware');

const AUTH_URL = process.env.AUTH_SERVICE_URL || 'http://localhost:8001';
const CHAT_URL = process.env.CHAT_SERVICE_URL || 'http://localhost:8002';

module.exports = function (app) {
  app.use(createProxyMiddleware('/api/auth', { target: AUTH_URL, changeOrigin: true }));
  app.use(createProxyMiddleware('/api/chat', { target: CHAT_URL, changeOrigin: true }));
  // WebSocket do chat (o /ws do próprio servidor de desenvolvimento não é afetado)
  app.use(createProxyMiddleware('/ws/chat', { target: CHAT_URL, changeOrigin: true, ws: true }));
};
