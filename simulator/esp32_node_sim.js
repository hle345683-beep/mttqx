/**
 * Mô phỏng nút thiết bị ESP32-WROOM-32 kết nối qua giao thức TCP (Cổng 1883)
 * Thực thi đúng máy trạng thái của firmware esp32_dt42_mqtt.ino:
 * - Khai báo LWT trên topic dt42/status: {"online":false} (Retain=true, QoS=1)
 * - Khi kết nối: Publish dt42/status: {"online":true} (Retain=true, QoS=1)
 * - Subscribe dt42/cmd (QoS 2) và dt42/sim_button (mô phỏng nhấn nút vật lý tại mạch)
 * - Mô phỏng độ trễ truyền dẫn Wi-Fi 802.11n + xử lý ngắt GPIO/Relay trên ESP32
 */

const mqtt = require('mqtt');

function startEsp32Node(options = {}) {
  const brokerUrl = options.brokerUrl || 'mqtt://127.0.0.1:1883';
  const clientId  = options.clientId  || 'esp32_dt42_node';
  const wifiBaseDelayMs = options.wifiBaseDelayMs ?? 12.0; // Độ trễ đường truyền Wi-Fi + TCP stack điển hình

  let relayPinState = false; // GPIO26 (false = LOW/OFF, true = HIGH/ON)
  let currentQoS = 1;

  const client = mqtt.connect(brokerUrl, {
    clientId,
    clean: true,
    keepalive: 15,
    reconnectPeriod: options.reconnectPeriod ?? 1000,
    protocolVersion: 4, // MQTT v3.1.1
    will: {
      topic: 'dt42/status',
      payload: JSON.stringify({ online: false }),
      qos: 1,
      retain: true
    }
  });

  function publishActualState(cmdId, tSend, qosLevel) {
    const payload = JSON.stringify({
      state: relayPinState ? 'ON' : 'OFF',
      cmd_id: cmdId,
      t_send: tSend,
      qos: qosLevel
    });
    client.publish('dt42/state', payload, { qos: qosLevel, retain: true });
  }

  client.on('connect', () => {
    client.publish('dt42/status', JSON.stringify({ online: true }), { qos: 1, retain: true });
    client.subscribe('dt42/cmd', { qos: 2 });
    client.subscribe('dt42/sim_button', { qos: 1 });
    publishActualState(0, 0, 1);
  });

  client.on('message', (topic, message, packet) => {
    if (topic === 'dt42/sim_button') {
      // Nút nhấn vật lý tại chỗ: đảo trạng thái Relay và gửi phản hồi với cmd_id = 0, t_send = 0
      relayPinState = !relayPinState;
      publishActualState(0, 0, currentQoS);
      return;
    }

    if (topic !== 'dt42/cmd') return;

    try {
      const data = JSON.parse(message.toString());
      const action = data.action;
      const cmdId  = Number(data.cmd_id || 0);
      const tSend  = Number(data.t_send || 0);
      const qos    = (typeof data.qos === 'number') ? data.qos : packet.qos;
      currentQoS   = qos;

      if (action === 'ON') {
        relayPinState = true;
      } else if (action === 'OFF') {
        relayPinState = false;
      } else if (action === 'TOGGLE') {
        relayPinState = !relayPinState;
      } else {
        return;
      }

      // Mô phỏng thời gian truyền dẫn Wi-Fi + giải mã JSON + đóng ngắt GPIO26 + bắt tay gói tin QoS trên ESP32
      // QoS 0: 1 gói PUBLISH/chặng; QoS 1: 2 gói (PUBLISH + PUBACK)/chặng; QoS 2: 4 gói (PUBLISH..PUBCOMP)/chặng
      const qosHandshakeOverhead = qos === 0 ? 0.0 : (qos === 1 ? 8.5 : 23.8);
      const jitter = (Math.random() - 0.5) * (qos === 0 ? 3.2 : (qos === 1 ? 4.0 : 5.4));
      const targetDelayMs = Math.max(2, wifiBaseDelayMs + qosHandshakeOverhead + jitter);
      const t0 = performance.now();

      function waitHighRes() {
        if (performance.now() - t0 >= targetDelayMs) {
          if (client.connected) {
            publishActualState(cmdId, tSend, qos);
          }
        } else {
          setImmediate(waitHighRes);
        }
      }
      setImmediate(waitHighRes);
    } catch (err) {
      // Bỏ qua bản tin sai định dạng JSON
    }
  });

  return {
    client,
    pressLocalButton: () => {
      relayPinState = !relayPinState;
      publishActualState(0, 0, currentQoS);
    },
    getRelayState: () => (relayPinState ? 'ON' : 'OFF')
  };
}

if (require.main === module) {
  startEsp32Node();
  console.log('[ESP32-Sim] Node started and connected to mqtt://127.0.0.1:1883');
}

module.exports = { startEsp32Node };
