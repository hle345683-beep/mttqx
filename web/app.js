/**
 * Đề tài ĐT42: Logic xử lý giao diện Web Dashboard (MQTT.js qua WebSocket)
 * - Chỉ cập nhật trạng thái hiển thị khi nhận bản tin từ dt42/state
 * - Đối chiếu cmd_id và t_send của lệnh đang chờ (pendingCmd) để tránh tính sai RTT
 *   khi nhận gói Retain hoặc khi thao tác nút nhấn vật lý (t_send = 0)
 */

(function () {
  const brokerInput  = document.getElementById('broker-url');
  const qosSelect    = document.getElementById('qos-select');
  const brokerBadge  = document.getElementById('broker-badge');
  const esp32Badge   = document.getElementById('esp32-badge');
  const relayEl      = document.getElementById('relay-state');
  const lastRttEl    = document.getElementById('last-rtt');
  const lastCmdIdEl  = document.getElementById('last-cmd-id');
  const btnOn        = document.getElementById('btn-on');
  const btnOff       = document.getElementById('btn-off');
  const btnLocal     = document.getElementById('btn-local');
  const btnBenchmark = document.getElementById('btn-benchmark');
  const btnExport    = document.getElementById('btn-export');
  const summaryTbody = document.getElementById('summary-tbody');
  const samplesTbody = document.getElementById('samples-tbody');
  const logBox       = document.getElementById('packet-log');

  let client = null;
  let esp32Online = false;
  let cmdCounter = 0;
  let pendingCmd = null; // { cmd_id, t_send, qos, resolve }

  const stats = {
    0: { sent: 0, rtts: [] },
    1: { sent: 0, rtts: [] },
    2: { sent: 0, rtts: [] }
  };

  function appendLog(line) {
    const ts = new Date().toISOString().slice(11, 23);
    logBox.textContent += `[${ts}] ${line}\n`;
    logBox.scrollTop = logBox.scrollHeight;
  }

  function initSampleRows() {
    samplesTbody.innerHTML = '';
    for (let i = 1; i <= 15; i++) {
      const rightIdx = i + 15;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${i}</td>
        <td id="cell-0-${i}">—</td>
        <td id="cell-1-${i}">—</td>
        <td id="cell-2-${i}">—</td>
        <td>${rightIdx}</td>
        <td id="cell-0-${rightIdx}">—</td>
        <td id="cell-1-${rightIdx}">—</td>
        <td id="cell-2-${rightIdx}">—</td>
      `;
      samplesTbody.appendChild(tr);
    }
  }

  function updateSummaryTable() {
    [0, 1, 2].forEach((q) => {
      const row = summaryTbody.querySelector(`tr[data-qos="${q}"]`);
      const s = stats[q];
      const count = s.rtts.length;
      const rate = s.sent > 0 ? ((count / s.sent) * 100).toFixed(1) : '—';
      let minStr = '—', maxStr = '—', meanStr = '—', sdStr = '—';

      if (count > 0) {
        const min = Math.min(...s.rtts);
        const max = Math.max(...s.rtts);
        const mean = s.rtts.reduce((a, b) => a + b, 0) / count;
        const variance = count > 1
          ? s.rtts.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / (count - 1)
          : 0;
        const sd = Math.sqrt(variance);
        minStr  = min.toFixed(2);
        maxStr  = max.toFixed(2);
        meanStr = mean.toFixed(2);
        sdStr   = sd.toFixed(2);
      }

      row.innerHTML = `
        <td>QoS ${q}</td>
        <td>${s.sent}</td>
        <td>${rate}</td>
        <td>${minStr}</td>
        <td>${maxStr}</td>
        <td>${meanStr}</td>
        <td>${sdStr}</td>
      `;

      s.rtts.slice(0, 30).forEach((val, idx) => {
        const cell = document.getElementById(`cell-${q}-${idx + 1}`);
        if (cell) cell.textContent = val.toFixed(2);
      });
    });
  }

  function setControlsEnabled(enabled) {
    btnOn.disabled = !enabled;
    btnOff.disabled = !enabled;
    btnLocal.disabled = !enabled;
    btnBenchmark.disabled = !enabled;
  }

  function sendCommand(action, qosOverride) {
    if (!client || !client.connected || !esp32Online) return Promise.resolve(null);
    const qos = typeof qosOverride === 'number' ? qosOverride : Number(qosSelect.value);
    cmdCounter += 1;
    const cmdId = cmdCounter;
    const tSend = Number((performance.now() + performance.timeOrigin).toFixed(2));
    stats[qos].sent += 1;
    updateSummaryTable();

    const payloadObj = { action, cmd_id: cmdId, t_send: tSend, qos };
    const payload = JSON.stringify(payloadObj);

    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        if (pendingCmd && pendingCmd.cmd_id === cmdId) {
          pendingCmd = null;
          appendLog(`TIMEOUT cmd_id=${cmdId} (QoS ${qos})`);
          resolve(null);
        }
      }, 3000);

      pendingCmd = { cmd_id: cmdId, t_send: tSend, qos, timer, resolve };
      appendLog(`PUB dt42/cmd [QoS ${qos}] ${payload}`);
      client.publish('dt42/cmd', payload, { qos });
    });
  }

  function connectBroker() {
    if (window.location.hostname && window.location.hostname !== '127.0.0.1' && window.location.hostname !== 'localhost') {
      const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      brokerInput.value = `${wsProto}//${window.location.host}/mqtt`;
    }
    const url = brokerInput.value.trim();
    client = mqtt.connect(url, {
      clientId: 'web_dashboard_dt42_' + Math.random().toString(16).slice(2, 6),
      clean: true,
      protocolVersion: 4
    });

    client.on('connect', () => {
      brokerBadge.textContent = 'Broker: Đã kết nối (WebSocket)';
      brokerBadge.className = 'badge badge-online';
      client.subscribe('dt42/state', { qos: 2 });
      client.subscribe('dt42/status', { qos: 1 });
      appendLog('Connected to Broker; Subscribed dt42/state (QoS 2), dt42/status (QoS 1)');
    });

    client.on('message', (topic, message, packet) => {
      const raw = message.toString();
      try {
        const data = JSON.parse(raw);
        if (topic === 'dt42/status') {
          esp32Online = Boolean(data.online);
          esp32Badge.textContent = esp32Online ? 'ESP32 (LWT): Online' : 'ESP32 (LWT): Offline';
          esp32Badge.className = esp32Online ? 'badge badge-online' : 'badge badge-offline';
          setControlsEnabled(esp32Online);
          appendLog(`RECV dt42/status [Retain=${packet.retain}] ${raw}`);
          return;
        }

        if (topic === 'dt42/state') {
          const stateStr = data.state === 'ON' ? 'ON' : 'OFF';
          relayEl.textContent = stateStr;
          relayEl.className = 'state-value ' + (stateStr === 'ON' ? 'state-on' : 'state-off');
          lastCmdIdEl.textContent = String(data.cmd_id ?? 0);

          // Chỉ tính RTT khi gói phản hồi khớp với lệnh đang chờ (pendingCmd) và t_send > 0
          if (pendingCmd && data.t_send > 0 && data.cmd_id === pendingCmd.cmd_id) {
            const tAck = Number((performance.now() + performance.timeOrigin).toFixed(2));
            const rtt = Math.max(0.1, tAck - Number(data.t_send));
            const q = pendingCmd.qos;
            clearTimeout(pendingCmd.timer);
            const done = pendingCmd.resolve;
            pendingCmd = null;

            stats[q].rtts.push(rtt);
            lastRttEl.textContent = `${rtt.toFixed(2)} ms`;
            appendLog(`RECV dt42/state [QoS ${packet.qos}] state=${stateStr} -> RTT=${rtt.toFixed(2)} ms`);
            updateSummaryTable();
            done(rtt);
          } else {
            // Bản tin Retain khi mới tải trang hoặc do nhấn nút vật lý tại chỗ (t_send = 0)
            lastRttEl.textContent = '— (Đồng bộ/Tại chỗ)';
            appendLog(`SYNC dt42/state [Retain=${packet.retain}] ${raw}`);
          }
        }
      } catch (e) {
        appendLog(`ERR parsing message on ${topic}`);
      }
    });
  }

  btnOn.addEventListener('click', () => sendCommand('ON'));
  btnOff.addEventListener('click', () => sendCommand('OFF'));
  btnLocal.addEventListener('click', () => {
    if (client && client.connected) {
      appendLog('SIM Local Button Press (GPIO27) -> t_send=0');
      client.publish('dt42/sim_button', '{"press":true}', { qos: 1 });
    }
  });

  btnBenchmark.addEventListener('click', async () => {
    setControlsEnabled(false);
    [0, 1, 2].forEach((q) => { stats[q].sent = 0; stats[q].rtts = []; });
    initSampleRows();
    updateSummaryTable();

    for (const q of [0, 1, 2]) {
      qosSelect.value = String(q);
      for (let i = 1; i <= 30; i++) {
        const action = (i % 2 === 1) ? 'ON' : 'OFF';
        await sendCommand(action, q);
        await new Promise((r) => setTimeout(r, 40));
      }
    }
    setControlsEnabled(esp32Online);
  });

  btnExport.addEventListener('click', () => {
    let csv = 'Lan_do,QoS_0_ms,QoS_1_ms,QoS_2_ms\n';
    for (let i = 0; i < 30; i++) {
      const v0 = stats[0].rtts[i] !== undefined ? stats[0].rtts[i].toFixed(2) : '';
      const v1 = stats[1].rtts[i] !== undefined ? stats[1].rtts[i].toFixed(2) : '';
      const v2 = stats[2].rtts[i] !== undefined ? stats[2].rtts[i].toFixed(2) : '';
      csv += `${i + 1},${v0},${v1},${v2}\n`;
    }
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'dt42_rtt_30_samples.csv';
    a.click();
  });

  initSampleRows();
  connectBroker();
})();
