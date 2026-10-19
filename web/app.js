/**
 * Đề tài ĐT42: Logic xử lý giao diện Web Dashboard (MQTT.js qua WebSocket)
 * - Bảo vệ truy cập bằng mật khẩu đăng nhập
 * - Hoạt động độc lập 24/7 trên Đám mây (Cloud EMQX Broker wss://broker.emqx.io:8084/mqtt)
 *   hoặc kết nối Local Broker / Wi-Fi ESP32
 * - Chỉ cập nhật trạng thái hiển thị khi nhận bản tin từ dt42/state
 */

(function () {
  const loginOverlay   = document.getElementById('login-overlay');
  const loginForm      = document.getElementById('login-form');
  const loginPass      = document.getElementById('login-pass');
  const loginError     = document.getElementById('login-error');
  const btnLogout      = document.getElementById('btn-logout');

  const brokerInput    = document.getElementById('broker-url');
  const btnReconnect   = document.getElementById('btn-reconnect');
  const qosSelect      = document.getElementById('qos-select');
  const cloudSimToggle = document.getElementById('cloud-sim-toggle');
  const brokerBadge    = document.getElementById('broker-badge');
  const esp32Badge     = document.getElementById('esp32-badge');
  const relayEl        = document.getElementById('relay-state');
  const lastRttEl      = document.getElementById('last-rtt');
  const lastCmdIdEl    = document.getElementById('last-cmd-id');
  const btnOn          = document.getElementById('btn-on');
  const btnOff         = document.getElementById('btn-off');
  const btnLocal       = document.getElementById('btn-local');
  const btnBenchmark   = document.getElementById('btn-benchmark');
  const btnExport      = document.getElementById('btn-export');
  const summaryTbody   = document.getElementById('summary-tbody');
  const samplesTbody   = document.getElementById('samples-tbody');
  const logBox         = document.getElementById('packet-log');

  const VALID_PASSWORDS = ['dt42', '123456', 'admin'];

  // Nếu chạy trên máy local (cổng 3000), dùng Local Broker; nếu mở trên Cloud (github.io...), dùng Cloud EMQX
  const isLocalServer = (window.location.port === '3000' || window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' || window.location.hostname.startsWith('192.168.'));
  if (isLocalServer && window.location.protocol === 'http:') {
    brokerInput.value = `ws://${window.location.host}/mqtt`;
    cloudSimToggle.checked = false; // Local server đã có simulator Node.js chạy sẵn
  } else {
    brokerInput.value = 'wss://broker.emqx.io:8084/mqtt';
    cloudSimToggle.checked = true;  // Trên Cloud tự động bật ESP32 ảo kết nối qua EMQX Cloud
  }

  let client = null;
  let simClient = null;
  let simRelayState = 'OFF';
  let esp32Online = false;
  let cmdCounter = 0;
  let pendingCmd = null;

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
      const rate = s.sent > 0 ? ((count / s.sent) * 100).toFixed(0) : '—';
      let minStr = '—', maxStr = '—', meanStr = '—';

      if (count > 0) {
        const min = Math.min(...s.rtts);
        const max = Math.max(...s.rtts);
        const mean = s.rtts.reduce((a, b) => a + b, 0) / count;
        minStr  = min.toFixed(2);
        maxStr  = max.toFixed(2);
        meanStr = mean.toFixed(2);
      }

      row.innerHTML = `
        <td>QoS ${q}</td>
        <td>${s.sent}</td>
        <td>${rate}</td>
        <td>${minStr}</td>
        <td>${maxStr}</td>
        <td>${meanStr}</td>
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

  // Khởi tạo ESP32 ảo kết nối trực tiếp lên Cloud EMQX Broker để hệ thống chạy 24/7 không cần bật PC
  function startCloudEsp32Sim(brokerUrl) {
    stopCloudEsp32Sim();
    if (!cloudSimToggle.checked) return;

    simClient = mqtt.connect(brokerUrl, {
      clientId: 'esp32_dt42_cloud_' + Math.random().toString(16).slice(2, 7),
      clean: true,
      protocolVersion: 4,
      will: {
        topic: 'dt42/status',
        payload: JSON.stringify({ online: false }),
        qos: 1,
        retain: true
      }
    });

    simClient.on('connect', () => {
      simClient.subscribe('dt42/cmd', { qos: 2 });
      simClient.subscribe('dt42/sim_button', { qos: 1 });
      simClient.publish('dt42/status', JSON.stringify({ online: true }), { qos: 1, retain: true });
      simClient.publish('dt42/state', JSON.stringify({ state: simRelayState, t_send: 0 }), { qos: 1, retain: true });
      appendLog('[ESP32-Cloud] Đã kết nối Broker và phát bản tin online=true');
    });

    simClient.on('message', (topic, message, packet) => {
      try {
        const data = JSON.parse(message.toString());
        if (topic === 'dt42/cmd') {
          if (data.action === 'ON' || data.action === 'OFF') {
            simRelayState = data.action;
          }
          const replyQos = typeof packet.qos === 'number' ? packet.qos : 1;
          setTimeout(() => {
            if (simClient && simClient.connected) {
              simClient.publish('dt42/state', JSON.stringify({
                state: simRelayState,
                t_send: data.t_send ?? 0
              }), { qos: replyQos, retain: true });
            }
          }, 4);
        } else if (topic === 'dt42/sim_button') {
          simRelayState = simRelayState === 'ON' ? 'OFF' : 'ON';
          simClient.publish('dt42/state', JSON.stringify({
            state: simRelayState,
            t_send: 0
          }), { qos: 1, retain: true });
        }
      } catch (err) {
        // ignore invalid json
      }
    });
  }

  function stopCloudEsp32Sim() {
    if (simClient) {
      try {
        if (simClient.connected) {
          simClient.publish('dt42/status', JSON.stringify({ online: false }), { qos: 1, retain: true });
        }
        simClient.end(true);
      } catch (e) {}
      simClient = null;
    }
  }

  function sendCommand(action, qosOverride) {
    if (!client || !client.connected || !esp32Online) return Promise.resolve(null);
    const qos = typeof qosOverride === 'number' ? qosOverride : Number(qosSelect.value);
    cmdCounter += 1;
    const tSend = Number((performance.now() + performance.timeOrigin).toFixed(2));
    stats[qos].sent += 1;
    lastCmdIdEl.textContent = String(cmdCounter);
    updateSummaryTable();

    const payloadObj = { action, t_send: tSend };
    const payload = JSON.stringify(payloadObj);

    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        if (pendingCmd && pendingCmd.t_send === tSend) {
          pendingCmd = null;
          appendLog(`TIMEOUT t_send=${tSend} (QoS ${qos})`);
          resolve(null);
        }
      }, 4000);

      pendingCmd = { t_send: tSend, qos, timer, resolve };
      appendLog(`PUB dt42/cmd [QoS ${qos}] ${payload}`);
      client.publish('dt42/cmd', payload, { qos });
    });
  }

  const reactorPanel   = document.getElementById('reactor-panel');
  const reactorStage   = document.getElementById('reactor-stage');
  const svgCoreState   = document.getElementById('svg-core-state');
  const coreModeLabel  = document.getElementById('core-mode-label');

  if (reactorStage) {
    reactorStage.style.cursor = 'pointer';
    reactorStage.title = 'Nhấn vào Lõi Năng Lượng HUY để Đóng/Ngắt Relay';
    reactorStage.addEventListener('click', () => {
      const nextAct = relayEl.textContent.trim() === 'ON' ? 'OFF' : 'ON';
      sendCommand(nextAct);
    });
  }

  function connectBroker() {
    if (client) {
      try { client.end(true); } catch (e) {}
      client = null;
    }
    const url = brokerInput.value.trim();
    brokerBadge.textContent = 'UPLINK: CONNECTING...';
    brokerBadge.className = 'hud-pill pill-offline';

    startCloudEsp32Sim(url);

    client = mqtt.connect(url, {
      clientId: 'web_dashboard_dt42_' + Math.random().toString(16).slice(2, 7),
      clean: true,
      protocolVersion: 4
    });

    client.on('connect', () => {
      brokerBadge.textContent = 'UPLINK: ONLINE';
      brokerBadge.className = 'hud-pill pill-online';
      client.subscribe('dt42/state', { qos: 2 });
      client.subscribe('dt42/status', { qos: 1 });
      appendLog(`Đã kết nối Broker (${url}); Đăng ký dt42/state, dt42/status`);
    });

    client.on('error', () => {
      brokerBadge.textContent = 'UPLINK: ERROR';
      brokerBadge.className = 'hud-pill pill-offline';
    });

    client.on('message', (topic, message, packet) => {
      const raw = message.toString();
      try {
        const data = JSON.parse(raw);
        if (topic === 'dt42/status') {
          esp32Online = Boolean(data.online);
          esp32Badge.textContent = esp32Online ? 'ESP32 UNIT: ONLINE' : 'ESP32 UNIT: OFFLINE';
          esp32Badge.className = esp32Online ? 'hud-pill pill-online' : 'hud-pill pill-offline';
          setControlsEnabled(esp32Online);
          appendLog(`RECV dt42/status [Retain=${packet.retain}] ${raw}`);
          return;
        }

        if (topic === 'dt42/state') {
          const stateStr = data.state === 'ON' ? 'ON' : 'OFF';
          relayEl.textContent = stateStr;
          relayEl.className = 'gauge-val ' + (stateStr === 'ON' ? 'state-on' : 'state-off');
          if (svgCoreState) svgCoreState.textContent = `RELAY: ${stateStr}`;
          if (coreModeLabel) coreModeLabel.textContent = stateStr === 'ON' ? 'CORE STATUS: ENGAGED' : 'CORE STATUS: STANDBY';
          if (reactorPanel) reactorPanel.classList.toggle('reactor-active', stateStr === 'ON');

          if (pendingCmd && data.t_send > 0 && Number(data.t_send) === pendingCmd.t_send) {
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
            lastRttEl.textContent = 'SYNC (0 ms)';
            appendLog(`SYNC dt42/state [Retain=${packet.retain}] ${raw}`);
          }
        }
      } catch (e) {
        appendLog(`ERR parsing message on ${topic}`);
      }
    });
  }

  // Xử lý đăng nhập mật khẩu
  function checkAuth() {
    if (sessionStorage.getItem('dt42_auth') === '1') {
      loginOverlay.hidden = true;
      connectBroker();
    } else {
      loginOverlay.hidden = false;
      loginPass.focus();
    }
  }

  loginForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const val = loginPass.value.trim();
    if (VALID_PASSWORDS.includes(val)) {
      sessionStorage.setItem('dt42_auth', '1');
      loginError.hidden = true;
      loginPass.value = '';
      loginOverlay.hidden = true;
      connectBroker();
    } else {
      loginError.hidden = false;
    }
  });

  btnLogout.addEventListener('click', () => {
    sessionStorage.removeItem('dt42_auth');
    stopCloudEsp32Sim();
    if (client) {
      try { client.end(true); } catch (e) {}
      client = null;
    }
    loginOverlay.hidden = false;
    loginPass.focus();
  });

  btnReconnect.addEventListener('click', () => connectBroker());
  cloudSimToggle.addEventListener('change', () => {
    if (cloudSimToggle.checked) {
      startCloudEsp32Sim(brokerInput.value.trim());
    } else {
      stopCloudEsp32Sim();
    }
  });

  btnOn.addEventListener('click', () => sendCommand('ON'));
  btnOff.addEventListener('click', () => sendCommand('OFF'));
  btnLocal.addEventListener('click', () => {
    if (client && client.connected) {
      appendLog('Nhấn nút tại chỗ (GPIO27) -> t_send=0');
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
        await new Promise((r) => setTimeout(r, 45));
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
  checkAuth();
})();
