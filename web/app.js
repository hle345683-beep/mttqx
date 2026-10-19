/**
 * Đề tài ĐT42: Hệ thống FUI Đa Lớp (Multi-Layer Interactive HUD)
 * - Lớp 0: Màn hình khóa bảo mật Neural Handshake
 * - Lớp 1: Tâm Lõi Bát Giác & Tua-bin Cơ Khí HUY (Core Standby)
 * - Lớp 2: Nhấn vào Lõi HUY -> Bung 4 Cánh Vệ Tinh & Mạch Dẫn (Orbital Sectors)
 * - Lớp 3: Mở từng Khoang Hologram Chức Năng (Relay / Đo RTT / Ma trận 30 mẫu / Uplink)
 */

(function () {
  const loginOverlay   = document.getElementById('login-overlay');
  const loginForm      = document.getElementById('login-form');
  const loginPass      = document.getElementById('login-pass');
  const loginError     = document.getElementById('login-error');
  const btnLogout      = document.getElementById('btn-logout');

  const fuiStage       = document.getElementById('fui-stage');
  const coreAssembly   = document.getElementById('core-assembly');
  const coreTrigger    = document.getElementById('central-core-trigger');
  const corePromptPill = document.getElementById('core-prompt-pill');
  const layerIndicator = document.getElementById('hud-layer-indicator');
  const svgCoreState   = document.getElementById('svg-core-state');

  // Mini readouts trên Lõi & Vệ tinh
  const hudMiniRtt     = document.getElementById('hud-mini-rtt');
  const hudMiniSeq     = document.getElementById('hud-mini-seq');
  const wingRelayVal   = document.getElementById('wing-relay-val');
  const wingRttVal     = document.getElementById('wing-rtt-val');
  const wingSeqVal     = document.getElementById('wing-seq-val');

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
  const MODALS = ['mod-control', 'mod-benchmark', 'mod-matrix', 'mod-uplink'];

  const isLocalServer = (
    window.location.port === '3000' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname === 'localhost' ||
    window.location.hostname.startsWith('192.168.')
  );
  if (isLocalServer && window.location.protocol === 'http:') {
    brokerInput.value = `ws://${window.location.host}/mqtt`;
    cloudSimToggle.checked = false;
  } else {
    brokerInput.value = 'wss://broker.emqx.io:8084/mqtt';
    cloudSimToggle.checked = true;
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

  // =========================================================================
  // ĐIỀU HƯỚNG ĐA LỚP (LAYER 1 <-> LAYER 2 <-> LAYER 3)
  // =========================================================================
  function setDockActive(targetId) {
    document.querySelectorAll('.dock-orb').forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('data-target') === targetId);
    });
  }

  function closeAllModals() {
    MODALS.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.hidden = true;
    });
    fuiStage.classList.remove('modal-open');
    const isExpanded = coreAssembly.classList.contains('expanded');
    layerIndicator.textContent = isExpanded
      ? 'LAYER 02 // ORBITAL SECTORS DEPLOYED'
      : 'LAYER 01 // CORE STANDBY';
    setDockActive('core');
  }

  function openModal(modId) {
    MODALS.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.hidden = (id !== modId);
    });
    fuiStage.classList.add('modal-open');
    const titles = {
      'mod-control':   'LAYER 03 // SECTOR 01: ACTUATOR CONTROL',
      'mod-benchmark': 'LAYER 03 // SECTOR 02: QoS RTT ANALYZER',
      'mod-matrix':    'LAYER 03 // SECTOR 03: TELEMETRY MATRIX',
      'mod-uplink':    'LAYER 03 // SECTOR 04: UPLINK & BUS'
    };
    layerIndicator.textContent = titles[modId] || 'LAYER 03 // MODULE ACTIVE';
    setDockActive(modId);
  }

  // Nhấn vào Tâm Lõi HUY -> Bung / Thu 4 cánh vệ tinh (Lớp 1 <-> Lớp 2)
  coreTrigger.addEventListener('click', () => {
    const nowExpanded = coreAssembly.classList.toggle('expanded');
    if (nowExpanded) {
      corePromptPill.innerHTML = '<span>[ CHỌN 1 TRONG 4 KHOANG VỆ TINH HOẶC NHẤN LÕI ĐỂ THU GỌN ]</span>';
      layerIndicator.textContent = 'LAYER 02 // ORBITAL SECTORS DEPLOYED';
    } else {
      corePromptPill.innerHTML = '<span>[ NHẤN VÀO LÕI HUY ĐỂ BUNG CÁC KHOANG ĐIỀU KHIỂN ]</span>';
      layerIndicator.textContent = 'LAYER 01 // CORE STANDBY';
    }
  });

  // Nhấn vào 1 trong 4 Cánh Vệ Tinh -> Mở Cửa sổ Hologram (Lớp 3)
  document.querySelectorAll('[data-open-mod]').forEach((wing) => {
    wing.addEventListener('click', () => {
      const targetMod = wing.getAttribute('data-open-mod');
      openModal(targetMod);
    });
  });

  // Chuyển nhanh giữa các Module (ví dụ từ Bảng tổng hợp sang Ma trận 30 mẫu)
  document.querySelectorAll('[data-switch-mod]').forEach((btn) => {
    btn.addEventListener('click', () => {
      openModal(btn.getAttribute('data-switch-mod'));
    });
  });

  // Nút đóng cửa sổ Module
  document.querySelectorAll('[data-close-mod]').forEach((btn) => {
    btn.addEventListener('click', closeAllModals);
  });

  // Nhấn phím ESC để đóng lớp 3 về lớp 2, hoặc từ lớp 2 thu về lớp 1
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (fuiStage.classList.contains('modal-open')) {
        closeAllModals();
      } else if (coreAssembly.classList.contains('expanded')) {
        coreAssembly.classList.remove('expanded');
        corePromptPill.innerHTML = '<span>[ NHẤN VÀO LÕI HUY ĐỂ BUNG CÁC KHOANG ĐIỀU KHIỂN ]</span>';
        layerIndicator.textContent = 'LAYER 01 // CORE STANDBY';
      }
    }
  });

  // Cột Dock 5 nút tròn bên phải (Giống Hình 1)
  document.querySelectorAll('.dock-orb').forEach((orb) => {
    orb.addEventListener('click', () => {
      const target = orb.getAttribute('data-target');
      if (target === 'core') {
        closeAllModals();
        coreAssembly.classList.toggle('expanded');
        const isExp = coreAssembly.classList.contains('expanded');
        corePromptPill.innerHTML = isExp
          ? '<span>[ CHỌN 1 TRONG 4 KHOANG VỆ TINH HOẶC NHẤN LÕI ĐỂ THU GỌN ]</span>'
          : '<span>[ NHẤN VÀO LÕI HUY ĐỂ BUNG CÁC KHOANG ĐIỀU KHIỂN ]</span>';
        layerIndicator.textContent = isExp
          ? 'LAYER 02 // ORBITAL SECTORS DEPLOYED'
          : 'LAYER 01 // CORE STANDBY';
      } else {
        coreAssembly.classList.add('expanded');
        openModal(target);
      }
    });
  });

  // =========================================================================
  // XỬ LÝ MQTT, VÒNG KÍN TRẠNG THÁI & ĐO ĐỘ TRỄ RTT
  // =========================================================================
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
    let totalSamples = 0;
    [0, 1, 2].forEach((q) => {
      const row = summaryTbody.querySelector(`tr[data-qos="${q}"]`);
      const s = stats[q];
      const count = s.rtts.length;
      totalSamples += count;
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

    if (wingSeqVal) wingSeqVal.textContent = `${totalSamples} / 90`;
  }

  function setControlsEnabled(enabled) {
    btnOn.disabled = !enabled;
    btnOff.disabled = !enabled;
    btnLocal.disabled = !enabled;
    btnBenchmark.disabled = !enabled;
  }

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
      appendLog('[ESP32-Cloud] Online & Ready');
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
      } catch (err) {}
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
    if (hudMiniSeq) hudMiniSeq.textContent = String(cmdCounter);
    updateSummaryTable();

    const payload = JSON.stringify({ action, t_send: tSend });

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

  function connectBroker() {
    if (client) {
      try { client.end(true); } catch (e) {}
      client = null;
    }
    const url = brokerInput.value.trim();
    brokerBadge.textContent = 'UPLINK: CONNECTING';
    brokerBadge.className = 'fui-badge badge-off';

    startCloudEsp32Sim(url);

    client = mqtt.connect(url, {
      clientId: 'web_fui_dt42_' + Math.random().toString(16).slice(2, 7),
      clean: true,
      protocolVersion: 4
    });

    client.on('connect', () => {
      brokerBadge.textContent = 'UPLINK: ONLINE';
      brokerBadge.className = 'fui-badge badge-on';
      client.subscribe('dt42/state', { qos: 2 });
      client.subscribe('dt42/status', { qos: 1 });
      appendLog(`Connected to ${url}; Subscribed dt42/state, dt42/status`);
    });

    client.on('error', () => {
      brokerBadge.textContent = 'UPLINK: ERROR';
      brokerBadge.className = 'fui-badge badge-off';
    });

    client.on('message', (topic, message, packet) => {
      const raw = message.toString();
      try {
        const data = JSON.parse(raw);
        if (topic === 'dt42/status') {
          esp32Online = Boolean(data.online);
          esp32Badge.textContent = esp32Online ? 'ESP32: ONLINE' : 'ESP32: OFFLINE';
          esp32Badge.className = esp32Online ? 'fui-badge badge-on' : 'fui-badge badge-off';
          setControlsEnabled(esp32Online);
          appendLog(`RECV dt42/status [Retain=${packet.retain}] ${raw}`);
          return;
        }

        if (topic === 'dt42/state') {
          const stateStr = data.state === 'ON' ? 'ON' : 'OFF';
          const isOn = stateStr === 'ON';

          relayEl.textContent = stateStr;
          relayEl.className = 'ro-value ' + (isOn ? 'state-on' : 'state-off');
          if (svgCoreState) svgCoreState.textContent = `RELAY: ${stateStr}`;
          if (wingRelayVal) {
            wingRelayVal.textContent = stateStr;
            wingRelayVal.className = isOn ? 'val-on' : 'val-off';
          }
          coreAssembly.classList.toggle('relay-on', isOn);

          if (pendingCmd && data.t_send > 0 && Number(data.t_send) === pendingCmd.t_send) {
            const tAck = Number((performance.now() + performance.timeOrigin).toFixed(2));
            const rtt = Math.max(0.1, tAck - Number(data.t_send));
            const rttStr = `${rtt.toFixed(2)} ms`;
            const q = pendingCmd.qos;
            clearTimeout(pendingCmd.timer);
            const done = pendingCmd.resolve;
            pendingCmd = null;

            stats[q].rtts.push(rtt);
            lastRttEl.textContent = rttStr;
            if (hudMiniRtt) hudMiniRtt.textContent = rttStr;
            if (wingRttVal) wingRttVal.textContent = rttStr;
            appendLog(`RECV dt42/state [QoS ${packet.qos}] state=${stateStr} -> RTT=${rttStr}`);
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
    closeAllModals();
    coreAssembly.classList.remove('expanded');
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
      appendLog('Local Button Override (GPIO27) -> t_send=0');
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
