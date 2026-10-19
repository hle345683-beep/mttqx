/**
 * Khởi chạy đồng thời:
 * 1. MQTT Broker (TCP :1883, WebSocket :8083/mqtt) + Web Dashboard (http://127.0.0.1:3000)
 * 2. Nút mô phỏng ESP32-WROOM-32 kết nối vào cổng TCP :1883
 */
const { startServers } = require('./server');
const { startEsp32Node } = require('./simulator/esp32_node_sim');

async function main() {
  await startServers();
  startEsp32Node({ wifiBaseDelayMs: 14.2 });
  console.log('[ESP32-Sim]      Đã kết nối vào Broker (mqtt://127.0.0.1:1883)');
  console.log('------------------------------------------------------------');
  console.log('=> Mở trình duyệt tại: http://127.0.0.1:3000');
  console.log('   Nhấn Ctrl+C để dừng hệ thống.');
}

main();
