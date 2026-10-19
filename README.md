# ĐT42: Hệ thống điều khiển thiết bị sử dụng MQTT (`mttqx`)

Dự án thực nghiệm và đánh giá độ trễ truyền thông cho đề tài **ĐT42 — Hệ thống điều khiển thiết bị sử dụng MQTT** (Học phần: Internet of Things – Mã LHP: `011100088401`, Học viện Hàng không Việt Nam).

## 1. Kiến trúc hệ thống & Quy hoạch Topic

Hệ thống hoạt động theo cơ chế điều khiển vòng kín (Closed-loop state feedback) qua giao thức **MQTT v3.1.1**:
- **Web Dashboard (`MQTT.js`)**: Kết nối Broker qua WebSocket (`ws://127.0.0.1:8083/mqtt`), phát lệnh điều khiển kèm mã phiên `cmd_id` và nhãn thời gian `t_send`, chỉ cập nhật trạng thái hiển thị khi nhận bản tin phản hồi thực tế từ `dt42/state` và tính độ trễ khứ hồi $\mathrm{RTT} = t_{\mathrm{ack}} - t_{\mathrm{send}}$ khi `cmd_id` khớp với phiên lệnh đang chờ.
- **MQTT Broker (`EMQX` / `Aedes`)**: Lắng nghe kết nối TCP tại cổng `1883` và WebSocket tại cổng `8083/mqtt`, định tuyến bản tin theo mức QoS (0, 1, 2), lưu giữ bản tin `Retain` và phát bản tin di chúc `LWT` khi thiết bị mất kết nối đột ngột.
- **Khối chấp hành (`ESP32-WROOM-32` & Module Relay)**: Kết nối Broker qua TCP (`1883`), điều khiển Relay tại chân `GPIO26`, đọc nút nhấn tại chỗ tại chân `GPIO27` (`INPUT_PULLUP`, chống dội 50 ms), đọc lại trạng thái thực tế của `GPIO26` và phản hồi lên `dt42/state`.

| Topic | Chiều truyền | Định dạng gói tin JSON | Cờ Retain | Chức năng |
| :--- | :--- | :--- | :---: | :--- |
| `dt42/cmd` | Web $\rightarrow$ Broker $\rightarrow$ ESP32 | `{"action":"ON","cmd_id":1,"t_send":1729301000120,"qos":1}` | `false` | Gửi lệnh đóng/ngắt (`ON`/`OFF`), kèm mã lệnh `cmd_id` và thời điểm phát $t_{\mathrm{send}}$ (ms). |
| `dt42/state` | ESP32 $\rightarrow$ Broker $\rightarrow$ Web | `{"state":"ON","cmd_id":1,"t_send":1729301000120,"qos":1}` | `true` | Phản hồi trạng thái thực tế của chân `GPIO26`; trả lại `cmd_id` và $t_{\mathrm{send}}$ (bằng `0` nếu nhấn nút tại chỗ). |
| `dt42/status` | ESP32 / Broker $\rightarrow$ Web | `{"online":true}` hoặc `{"online":false}` | `true` | Giám sát kết nối thiết bị; Broker tự động phát `{"online":false}` theo cơ chế LWT khi mất kết nối. |

## 2. Cấu trúc thư mục

```text
mttqx/
├── firmware/
│   └── esp32_dt42_mqtt/
│       └── esp32_dt42_mqtt.ino   # Mã nguồn vi điều khiển ESP32 (Arduino/ESP-IDF)
├── simulator/
│   └── esp32_node_sim.js         # Nút mô phỏng ESP32 qua giao thức TCP (:1883)
├── web/
│   ├── index.html                # Giao diện điều khiển và đo kiểm Web Dashboard
│   ├── style.css                 # Định dạng giao diện kỹ thuật
│   └── app.js                    # Xử lý MQTT.js, đồng bộ trạng thái và đo RTT
├── benchmark/
│   ├── run_benchmark.js          # Kịch bản kiểm thử chức năng & đo tự động 30 mẫu × 3 mức QoS
│   ├── generate_figures.py       # Script xuất 8 sơ đồ kỹ thuật và biểu đồ RTT (300 DPI)
│   ├── results.json              # Kết quả kiểm thử chức năng và thống kê RTT
│   └── results_30_samples.csv    # Dữ liệu thô 30 lần đo của QoS 0, QoS 1, QoS 2
├── docs/
│   └── figures/                  # Các hình vẽ kỹ thuật và biểu đồ chuẩn hóa (300 DPI)
├── server.js                     # MQTT Broker (TCP :1883, WS :8083/mqtt) & Web Server (:3000)
└── package.json
```

## 3. Hướng dẫn chạy và đo kiểm

1. Cài đặt thư viện phụ thuộc:
   ```bash
   npm install
   ```
2. Chạy kịch bản kiểm thử chức năng và đo tự động 30 mẫu × 3 mức QoS:
   ```bash
   npm run benchmark
   ```
3. Khởi chạy hệ thống tương tác trực tiếp trên trình duyệt (`http://127.0.0.1:3000`):
   ```bash
   npm start
   # Mở terminal thứ hai để chạy nút ESP32 mô phỏng:
   npm run sim
   ```

## 4. Tóm tắt kết quả thực nghiệm (30 lần đo / mức QoS)

| Mức QoS | Số lệnh phát | Tỷ lệ phản hồi (%) | RTT nhỏ nhất (ms) | RTT lớn nhất (ms) | RTT trung bình (ms) | Độ lệch chuẩn SD (ms) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **QoS 0** | 30 | 100,0% | 13,64 | 17,03 | 15,26 | 0,94 |
| **QoS 1** | 30 | 100,0% | 22,09 | 26,40 | 23,88 | 1,23 |
| **QoS 2** | 30 | 100,0% | 37,12 | 42,47 | 39,43 | 1,38 |
