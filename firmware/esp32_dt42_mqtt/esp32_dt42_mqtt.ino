/**
 * Đề tài ĐT42: Hệ thống điều khiển thiết bị sử dụng MQTT
 * Phần cứng: ESP32-WROOM-32 + Module Relay 1 kênh + Nút nhấn tại chỗ
 * Thư viện: WiFi.h (Espressif), MQTT.h (256dpi/arduino-mqtt), ArduinoJson.h
 */

#include <WiFi.h>
#include <MQTT.h>
#include <ArduinoJson.h>

// Cấu hình mạng Wi-Fi và MQTT Broker (EMQX)
const char* WIFI_SSID     = "IOT_LAB_24GHz";
const char* WIFI_PASSWORD = "password123";
const char* MQTT_HOST     = "192.168.1.100";
const int   MQTT_PORT     = 1883;
const char* MQTT_CLIENTID = "esp32_dt42_node";

// Định nghĩa chân GPIO
const uint8_t PIN_RELAY  = 26; // Ngõ ra điều khiển Relay (mức HIGH đóng tiếp điểm NO)
const uint8_t PIN_BUTTON = 27; // Ngõ vào nút nhấn tại chỗ (kéo lên nội INPUT_PULLUP)
const uint8_t PIN_LED    = 2;  // LED báo trạng thái kết nối Broker

// Cấu trúc Topic
const char* TOPIC_CMD    = "dt42/cmd";
const char* TOPIC_STATE  = "dt42/state";
const char* TOPIC_STATUS = "dt42/status";

WiFiClient net;
MQTTClient client(512);

bool relayState = false;
int  currentQoS = 1;

// Biến chống dội phím (Debounce 50 ms)
bool lastReading = HIGH;
bool buttonStableState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long DEBOUNCE_MS = 50;

/**
 * Đọc trạng thái thực tế của chân điều khiển Relay và gửi bản tin phản hồi dt42/state
 */
void publishActualState(uint32_t cmdId, uint64_t tSend, int qosLevel) {
  bool actualPin = (digitalRead(PIN_RELAY) == HIGH);
  relayState = actualPin;

  StaticJsonDocument<128> doc;
  doc["state"]  = actualPin ? "ON" : "OFF";
  doc["cmd_id"] = cmdId;
  doc["t_send"] = tSend;
  doc["qos"]    = qosLevel;

  char payload[128];
  serializeJson(doc, payload, sizeof(payload));

  // Gửi bản tin trạng thái thực tế với cờ Retain = true và mức QoS tương ứng
  client.publish(TOPIC_STATE, payload, true, qosLevel);
}

/**
 * Hàm callback xử lý khi nhận bản tin từ MQTT Broker
 */
void onMessageReceived(String &topic, String &payload) {
  if (topic != TOPIC_CMD) return;

  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, payload);
  if (err) return;

  const char* action = doc["action"] | "";
  uint32_t cmdId     = doc["cmd_id"] | 0;
  uint64_t tSend     = doc["t_send"] | 0ULL;
  int qos            = doc["qos"]    | currentQoS;

  if (qos >= 0 && qos <= 2) {
    currentQoS = qos;
  }

  if (strcmp(action, "ON") == 0) {
    digitalWrite(PIN_RELAY, HIGH);
  } else if (strcmp(action, "OFF") == 0) {
    digitalWrite(PIN_RELAY, LOW);
  } else if (strcmp(action, "TOGGLE") == 0) {
    digitalWrite(PIN_RELAY, !digitalRead(PIN_RELAY));
  } else {
    return;
  }

  // Bước 3: Đọc trạng thái thực tế của chân GPIO26 và phản hồi về dt42/state
  publishActualState(cmdId, tSend, currentQoS);
}

/**
 * Kết nối Wi-Fi và MQTT Broker kèm khai báo Last Will and Testament (LWT)
 */
void ensureConnected() {
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(PIN_LED, LOW);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
      delay(250);
    }
  }

  if (!client.connected()) {
    digitalWrite(PIN_LED, LOW);
    // Đăng ký LWT: Broker tự động phát {"online":false} (Retain=true, QoS=1) khi mất kết nối
    client.setWill(TOPIC_STATUS, "{\"online\":false}", true, 1);

    while (!client.connect(MQTT_CLIENTID)) {
      delay(500);
    }

    digitalWrite(PIN_LED, HIGH);
    // Thông báo thiết bị trực tuyến (Retain=true, QoS=1)
    client.publish(TOPIC_STATUS, "{\"online\":true}", true, 1);
    // Đăng ký nhận lệnh ở mức QoS tối đa (QoS 2) để hỗ trợ mọi mức QoS thử nghiệm
    client.subscribe(TOPIC_CMD, 2);
    // Đồng bộ trạng thái thực tế ban đầu lên Broker
    publishActualState(0, 0, 1);
  }
}

/**
 * Quét nút nhấn tại chỗ có chống dội phím (50 ms)
 */
void pollLocalButton() {
  bool reading = digitalRead(PIN_BUTTON);
  if (reading != lastReading) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > DEBOUNCE_MS) {
    if (reading != buttonStableState) {
      buttonStableState = reading;
      if (buttonStableState == LOW) { // Nhấn nút (mức tích cực thấp)
        digitalWrite(PIN_RELAY, !digitalRead(PIN_RELAY));
        // Nút nhấn tại chỗ: cmd_id = 0, t_send = 0
        publishActualState(0, 0, currentQoS);
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

  WiFi.mode(WIFI_STA);
  client.begin(MQTT_HOST, MQTT_PORT, net);
  client.onMessage(onMessageReceived);
  client.setOptions(15, true, 3000); // Keep-alive 15s, cleanSession=true, timeout 3000ms

  ensureConnected();
}

void loop() {
  client.loop();
  if (!client.connected()) {
    ensureConnected();
  }
  pollLocalButton();
}
