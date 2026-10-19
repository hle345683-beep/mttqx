/**
 * Đề tài ĐT42: Hệ thống điều khiển thiết bị sử dụng MQTT
 * Phần cứng: ESP32 + Module Relay + Nút nhấn tại chỗ
 * Hỗ trợ đồng thời:
 *   1. Kết nối Cloud EMQX Broker (broker.emqx.io:1883) để điều khiển từ Web trên đám mây
 *   2. Phát Wi-Fi riêng "ESP32-DT42" (mật khẩu: 12345678) kèm trang đăng nhập Captive Portal (192.168.4.1)
 */

#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <MQTT.h>
#include <ArduinoJson.h>

// 1. Cấu hình Wi-Fi nhà (Station) & Cloud EMQX Broker
const char* WIFI_SSID     = "IOT_LAB_24GHz";
const char* WIFI_PASSWORD = "password123";
const char* MQTT_HOST     = "broker.emqx.io";
const int   MQTT_PORT     = 1883;
const char* MQTT_CLIENTID = "esp32_dt42_node";

// 2. Cấu hình Wi-Fi phát ra từ ESP32 (Access Point) & Mật khẩu đăng nhập Web
const char* AP_SSID       = "ESP32-DT42";
const char* AP_PASS       = "12345678";
const char* WEB_PASS      = "dt42";
const char* CLOUD_WEB_URL = "https://hle345683-beep.github.io/mttqx/";

// Định nghĩa chân GPIO
const uint8_t PIN_RELAY  = 26;
const uint8_t PIN_BUTTON = 27;
const uint8_t PIN_LED    = 2;

// Cấu trúc Topic
const char* TOPIC_CMD    = "dt42/cmd";
const char* TOPIC_STATE  = "dt42/state";
const char* TOPIC_STATUS = "dt42/status";

WiFiClient net;
MQTTClient client(512);
WebServer  portalServer(80);
DNSServer  dnsServer;

bool relayState = false;
int  currentQoS = 1;

bool lastReading = HIGH;
bool buttonStableState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long DEBOUNCE_MS = 50;

void publishActualState(uint64_t tSend, int qosLevel) {
  bool actualPin = (digitalRead(PIN_RELAY) == HIGH);
  relayState = actualPin;

  StaticJsonDocument<128> doc;
  doc["state"]  = actualPin ? "ON" : "OFF";
  doc["t_send"] = tSend;

  char payload[128];
  serializeJson(doc, payload, sizeof(payload));

  if (client.connected()) {
    client.publish(TOPIC_STATE, payload, true, qosLevel);
  }
}

void onMessageReceived(String &topic, String &payload) {
  if (topic != TOPIC_CMD) return;

  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, payload)) return;

  const char* action = doc["action"] | "";
  uint64_t tSend     = doc["t_send"] | 0ULL;

  if (strcmp(action, "ON") == 0) {
    digitalWrite(PIN_RELAY, HIGH);
  } else if (strcmp(action, "OFF") == 0) {
    digitalWrite(PIN_RELAY, LOW);
  } else {
    return;
  }

  publishActualState(tSend, currentQoS);
}

// Trang Web nhúng trực tiếp trên ESP32 khi kết nối Wi-Fi "ESP32-DT42" (http://192.168.4.1)
void setupCaptivePortal() {
  portalServer.on("/", HTTP_GET, []() {
    String html = F(
      "<!DOCTYPE html><html lang='vi'><head><meta charset='UTF-8'>"
      "<meta name='viewport' content='width=device-width,initial-scale=1'>"
      "<title>SYS.DT42 // ESP32 MECHATRONICS HUD</title>"
      "<style>body{font-family:Consolas,Arial,sans-serif;background:#06080c;color:#f8fafc;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;padding:16px}"
      ".card{background:#0c1017;padding:24px;max-width:390px;width:100%;border:1px solid #f59e0b;box-shadow:0 0 28px rgba(245,158,11,0.22)}"
      ".tag{font-size:10px;color:#fbbf24;letter-spacing:1.5px;margin-bottom:4px}"
      "h2{font-size:16px;color:#fff;margin:0 0 8px}p{font-size:12.5px;color:#94a3b8;margin:0 0 14px}"
      "input,button,a.btn{width:100%;padding:10px;margin-top:8px;box-sizing:border-box;font-family:Consolas,sans-serif;font-size:13px;text-align:center;display:block;text-decoration:none}"
      "input{background:#05070b;color:#fff;border:1px solid #f59e0b}"
      "button{background:#fbbf24;color:#000;border:none;font-weight:bold;cursor:pointer;text-transform:uppercase}"
      "a.btn{background:transparent;color:#fbbf24;border:1px solid #f59e0b;font-weight:bold}</style></head><body>"
      "<div class='card'><div class='tag'>J.A.R.V.I.S. // JAEGER NODE ĐT42</div>"
      "<h2>CỔNG ĐIỀU KHIỂN TRỰC TIẾP ESP32</h2>"
      "<p>Kết nối Wi-Fi nội bộ ESP32. Nhập mã khóa để đảo Relay hoặc mở HUD Đám mây:</p>"
      "<form action='/control' method='POST'>"
      "<input type='password' name='pwd' placeholder='Mã khóa (mặc định: dt42)' required>"
      "<button type='submit' name='act' value='TOGGLE'>ENGAGE // ĐẢO TRẠNG THÁI RELAY</button>"
      "</form>"
      "<a class='btn' href='https://hle345683-beep.github.io/mttqx/'>MỞ J.A.R.V.I.S. CLOUD HUD</a>"
      "</div></body></html>"
    );
    portalServer.send(200, "text/html; charset=utf-8", html);
  });

  portalServer.on("/control", HTTP_POST, []() {
    if (portalServer.arg("pwd") != WEB_PASS) {
      portalServer.send(403, "text/html; charset=utf-8", "<h3>Sai mật khẩu! <a href='/'>Quay lại</a></h3>");
      return;
    }
    digitalWrite(PIN_RELAY, !digitalRead(PIN_RELAY));
    publishActualState(0, currentQoS);
    portalServer.sendHeader("Location", "/");
    portalServer.send(303);
  });

  portalServer.onNotFound([]() {
    portalServer.sendHeader("Location", String("http://192.168.4.1/"), true);
    portalServer.send(302, "text/plain", "");
  });

  portalServer.begin();
}

void ensureConnected() {
  if (WiFi.status() == WL_CONNECTED && !client.connected()) {
    digitalWrite(PIN_LED, LOW);
    client.setWill(TOPIC_STATUS, "{\"online\":false}", true, 1);
    if (client.connect(MQTT_CLIENTID)) {
      digitalWrite(PIN_LED, HIGH);
      client.publish(TOPIC_STATUS, "{\"online\":true}", true, 1);
      client.subscribe(TOPIC_CMD, 2);
      publishActualState(0, 1);
    }
  }
}

void pollLocalButton() {
  bool reading = digitalRead(PIN_BUTTON);
  if (reading != lastReading) {
    lastDebounceTime = millis();
  }
  if ((millis() - lastDebounceTime) > DEBOUNCE_MS) {
    if (reading != buttonStableState) {
      buttonStableState = reading;
      if (buttonStableState == LOW) {
        digitalWrite(PIN_RELAY, !digitalRead(PIN_RELAY));
        publishActualState(0, currentQoS);
      }
    }
  }
  lastReading = reading;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_RELAY, OUTPUT);
  digitalWrite(PIN_RELAY, LOW);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, LOW);

  // Vừa phát Wi-Fi riêng "ESP32-DT42" (192.168.4.1), vừa kết nối Wi-Fi Internet tới Cloud EMQX
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(AP_SSID, AP_PASS);
  dnsServer.start(53, "*", WiFi.softAPIP());
  setupCaptivePortal();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  client.begin(MQTT_HOST, MQTT_PORT, net);
  client.onMessage(onMessageReceived);
  client.setOptions(15, true, 3000);
}

void loop() {
  dnsServer.processNextRequest();
  portalServer.handleClient();
  client.loop();
  ensureConnected();
  pollLocalButton();
}
