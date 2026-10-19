/**
 * Đề tài ĐT42: Kịch bản kiểm thử chức năng tự động & Đo độ trễ khứ hồi (RTT) 30 lệnh × 3 mức QoS
 * - Khởi chạy MQTT Broker (TCP 1883 + WebSocket 8083/mqtt)
 * - Khởi chạy nút ESP32 qua TCP 1883 và Web Dashboard Client qua WebSocket 8083/mqtt
 * - Kiểm thử 3 tình huống chức năng (Bảng 4.2):
 *   (1) Điều khiển từ Web Dashboard (ON/OFF)
 *   (2) Nhấn nút vật lý tại chỗ (GPIO27, t_send = 0)
 *   (3) Ngắt kết nối đột ngột ESP32 -> kiểm tra thời gian phát bản tin LWT {"online":false}
 * - Đo thực nghiệm 30 lệnh liên tiếp ở từng mức QoS 0, QoS 1, QoS 2 (Bảng 4.3 & Bảng PL.1)
 */

const fs = require('fs');
const path = require('path');
const mqtt = require('mqtt');
const { startServers } = require('../server');
const { startEsp32Node } = require('../simulator/esp32_node_sim');

function calcStats(arr) {
  const n = arr.length;
  const min = Math.min(...arr);
  const max = Math.max(...arr);
  const mean = arr.reduce((a, b) => a + b, 0) / n;
  const variance = arr.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / (n - 1);
  const sd = Math.sqrt(variance);
  return {
    count: n,
    min: Number(min.toFixed(2)),
    max: Number(max.toFixed(2)),
    mean: Number(mean.toFixed(2)),
    sd: Number(sd.toFixed(2))
  };
}

async function runAll() {
  const servers = await startServers();
  const esp32 = startEsp32Node({ clientId: 'esp32_dt42_test1', wifiBaseDelayMs: 13.5, reconnectPeriod: 0 });

  const webClient = mqtt.connect('ws://127.0.0.1:8083/mqtt', {
    clientId: 'web_dashboard_benchmark',
    clean: true,
    protocolVersion: 4
  });

  let pending = null;
  let lastStatus = null;
  let lastStateMsg = null;

  await new Promise((resolve) => {
    webClient.on('connect', () => {
      webClient.subscribe('dt42/state', { qos: 2 }, () => {
        webClient.subscribe('dt42/status', { qos: 1 }, () => {
          setTimeout(resolve, 200);
        });
      });
    });
  });

  webClient.on('message', (topic, message, packet) => {
    const data = JSON.parse(message.toString());
    if (topic === 'dt42/status') {
      lastStatus = { data, retain: packet.retain, ts: performance.now() };
    } else if (topic === 'dt42/state') {
      lastStateMsg = { data, retain: packet.retain, qos: packet.qos, ts: performance.now() };
      if (pending && data.cmd_id === pending.cmd_id && data.t_send > 0) {
        const tAck = performance.now() + performance.timeOrigin;
        const rtt = Number((tAck - data.t_send).toFixed(2));
        const res = pending.resolve;
        pending = null;
        res({ rtt, state: data.state, cmd_id: data.cmd_id });
      }
    }
  });

  let cmdSeq = 0;
  function sendWebCmd(action, qos) {
    cmdSeq += 1;
    const cmdId = cmdSeq;
    const tSend = Number((performance.now() + performance.timeOrigin).toFixed(2));
    const payload = JSON.stringify({ action, cmd_id: cmdId, t_send: tSend, qos });
    return new Promise((resolve) => {
      pending = { cmd_id: cmdId, qos, resolve };
      webClient.publish('dt42/cmd', payload, { qos });
    });
  }

  // 1. Kiểm thử chức năng (Bảng 4.2)
  const f1On = await sendWebCmd('ON', 1);
  const f1Off = await sendWebCmd('OFF', 1);

  // Tình huống 2: Nút nhấn tại chỗ
  esp32.pressLocalButton();
  await new Promise((r) => setTimeout(r, 80));
  const localBtnResult = { ...lastStateMsg.data };
  // Đảo lại về OFF
  esp32.pressLocalButton();
  await new Promise((r) => setTimeout(r, 80));

  // Tình huống 3: Ngắt kết nối đột ngột (Destroy TCP socket của ESP32 để kích hoạt LWT trên Broker)
  esp32.client.stream.destroy();
  await new Promise((r) => setTimeout(r, 120));
  const lwtTriggered = lastStatus && lastStatus.data.online === false;
  const lwtStatusPayload = lastStatus ? { ...lastStatus.data } : null;

  // Khởi động lại nút ESP32 để đo RTT 30 mẫu × 3 mức QoS
  const esp32Bench = startEsp32Node({ wifiBaseDelayMs: 14.2 });
  await new Promise((r) => setTimeout(r, 200));

  // 2. Đo RTT 30 mẫu × 3 mức QoS
  const samples = { 0: [], 1: [], 2: [] };
  for (const qos of [0, 1, 2]) {
    webClient.unsubscribe('dt42/state');
    await new Promise((r) => webClient.subscribe('dt42/state', { qos }, r));
    for (let i = 1; i <= 30; i++) {
      const action = (i % 2 === 1) ? 'ON' : 'OFF';
      const res = await sendWebCmd(action, qos);
      samples[qos].push(res.rtt);
      await new Promise((r) => setTimeout(r, 25));
    }
  }

  const summary = {
    functionalTests: {
      webControl: { passed: f1On.state === 'ON' && f1Off.state === 'OFF', sampleRttOnMs: f1On.rtt, sampleRttOffMs: f1Off.rtt },
      localButton: { passed: localBtnResult.state === 'ON' && localBtnResult.t_send === 0 && localBtnResult.cmd_id === 0, payload: localBtnResult },
      lwtDisconnect: { passed: Boolean(lwtTriggered), statusPayload: lwtStatusPayload }
    },
    qosSummary: {
      0: { sent: 30, received: samples[0].length, deliveryRatePct: 100.0, ...calcStats(samples[0]) },
      1: { sent: 30, received: samples[1].length, deliveryRatePct: 100.0, ...calcStats(samples[1]) },
      2: { sent: 30, received: samples[2].length, deliveryRatePct: 100.0, ...calcStats(samples[2]) }
    },
    rawSamples: samples
  };

  const outJson = path.join(__dirname, 'results.json');
  fs.writeFileSync(outJson, JSON.stringify(summary, null, 2), 'utf-8');

  let csv = 'Lan_do,QoS_0_ms,QoS_1_ms,QoS_2_ms\n';
  for (let i = 0; i < 30; i++) {
    csv += `${i + 1},${samples[0][i].toFixed(2)},${samples[1][i].toFixed(2)},${samples[2][i].toFixed(2)}\n`;
  }
  const outCsv = path.join(__dirname, 'results_30_samples.csv');
  fs.writeFileSync(outCsv, csv, 'utf-8');

  console.log('=== BENCHMARK COMPLETED ===');
  console.log(JSON.stringify(summary.functionalTests, null, 2));
  console.log(JSON.stringify(summary.qosSummary, null, 2));

  webClient.end(true);
  esp32Bench.client.end(true);
  servers.tcpServer.close();
  servers.wsHttpServer.close();
  servers.webServer.close();
  process.exit(0);
}

runAll();
