/**
 * Đề tài ĐT42: MQTT Broker (Aedes/EMQX-compatible) + Static Web Dashboard Server
 * - MQTT over TCP: port 1883 (dành cho ESP32)
 * - MQTT over WebSocket: port 8083, path /mqtt (dành cho Web Dashboard)
 * - HTTP Web Dashboard: port 8080
 */

const fs = require('fs');
const path = require('path');
const net = require('net');
const http = require('http');
const aedes = require('aedes')();
const { WebSocketServer } = require('ws');
const websocketStream = require('websocket-stream');

const TCP_PORT = Number(process.env.MQTT_TCP_PORT || 1883);
const WS_PORT  = Number(process.env.MQTT_WS_PORT  || 8083);
const WEB_PORT = Number(process.env.WEB_PORT      || 3000);

// 1. Khởi tạo MQTT Broker qua TCP (Cổng 1883 cho ESP32)
const tcpServer = net.createServer(aedes.handle);

// 2. Khởi tạo MQTT Broker qua WebSocket (Cổng 8083/mqtt cho Web Dashboard)
const wsHttpServer = http.createServer();
const wss = new WebSocketServer({ server: wsHttpServer, path: '/mqtt' });
wss.on('connection', (ws, req) => {
  const stream = websocketStream(ws, { binary: true });
  aedes.handle(stream, req);
});

// 3. Khởi tạo HTTP Server phục vụ giao diện Web Dashboard (Cổng 8080)
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.js':   'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.csv':  'text/csv; charset=utf-8',
  '.png':  'image/png'
};

const webDir = path.join(__dirname, 'web');
const nodeModulesMqtt = path.join(__dirname, 'node_modules', 'mqtt', 'dist', 'mqtt.min.js');

const webServer = http.createServer((req, res) => {
  const urlPath = req.url.split('?')[0];
  if (urlPath === '/mqtt.min.js' && fs.existsSync(nodeModulesMqtt)) {
    res.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8' });
    fs.createReadStream(nodeModulesMqtt).pipe(res);
    return;
  }
  const safePath = urlPath === '/' ? '/index.html' : urlPath;
  const filePath = path.join(webDir, path.normalize(safePath));
  if (!filePath.startsWith(webDir) || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('404 Not Found');
    return;
  }
  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
  fs.createReadStream(filePath).pipe(res);
});

function startServers() {
  return new Promise((resolve) => {
    tcpServer.listen(TCP_PORT, '127.0.0.1', () => {
      wsHttpServer.listen(WS_PORT, '127.0.0.1', () => {
        webServer.listen(WEB_PORT, '127.0.0.1', () => {
          console.log(`[MQTT-TCP]       mqtt://127.0.0.1:${TCP_PORT}`);
          console.log(`[MQTT-WebSocket] ws://127.0.0.1:${WS_PORT}/mqtt`);
          console.log(`[Web-Dashboard]  http://127.0.0.1:${WEB_PORT}`);
          resolve({ aedes, tcpServer, wsHttpServer, webServer });
        });
      });
    });
  });
}

if (require.main === module) {
  startServers();
}

module.exports = { startServers, aedes };
