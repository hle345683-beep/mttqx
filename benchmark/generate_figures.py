import os, json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Polygon, FancyArrowPatch

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['axes.unicode_minus'] = False

OUT_DIR = r'C:\Users\Admin\Documents\GitHub\mttqx\docs\figures'
os.makedirs(OUT_DIR, exist_ok=True)

# Bảng màu kỹ thuật chuẩn IEEE (trung tính, độ tương phản cao khi in trắng đen hoặc xem màu)
C_NAVY   = '#1B365D'
C_NAVY_L = '#E8EEF5'
C_SLATE  = '#334155'
C_GRAY_L = '#F1F5F9'
C_GREEN  = '#1E5631'
C_GREEN_L= '#E9F3EC'
C_AMBER  = '#7C4700'
C_AMBER_L= '#FEF3C7'
C_RED    = '#8B1E1E'
C_TEXT   = '#111827'

def draw_box(ax, x, y, w, h, text, fc='#FFFFFF', ec=C_SLATE, lw=1.4, fontsize=10.5, fontweight='normal', tc=C_TEXT, rounding=0.02, subtext=None):
    box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                         boxstyle=f"round,pad=0,rounding_size={rounding}",
                         facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3)
    ax.add_patch(box)
    if subtext:
        ax.text(x, y + h*0.14, text, ha='center', va='center', fontsize=fontsize, fontweight='bold', color=tc, zorder=4)
        ax.text(x, y - h*0.18, subtext, ha='center', va='center', fontsize=fontsize-1, fontweight='normal', color=C_SLATE, zorder=4)
    else:
        ax.text(x, y, text, ha='center', va='center', fontsize=fontsize, fontweight=fontweight, color=tc, zorder=4)

def draw_oval(ax, x, y, w, h, text, fc=C_NAVY_L, ec=C_NAVY, fontsize=10.5):
    box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                         boxstyle=f"round,pad=0,rounding_size={h/2}",
                         facecolor=fc, edgecolor=ec, linewidth=1.5, zorder=3)
    ax.add_patch(box)
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize, fontweight='bold', color=C_NAVY, zorder=4)

def draw_diamond(ax, x, y, w, h, text, fc='#FFFFFF', ec=C_SLATE, fontsize=10):
    pts = [[x, y + h/2], [x + w/2, y], [x, y - h/2], [x - w/2, y]]
    poly = Polygon(pts, closed=True, facecolor=fc, edgecolor=ec, linewidth=1.4, zorder=3)
    ax.add_patch(poly)
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize, color=C_TEXT, zorder=4)

def draw_parallelogram(ax, x, y, w, h, text, fc=C_GREEN_L, ec=C_GREEN, fontsize=10, skew=0.18):
    dx = h * skew
    pts = [[x - w/2 + dx, y + h/2], [x + w/2 + dx, y + h/2],
           [x + w/2 - dx, y - h/2], [x - w/2 - dx, y - h/2]]
    poly = Polygon(pts, closed=True, facecolor=fc, edgecolor=ec, linewidth=1.4, zorder=3)
    ax.add_patch(poly)
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize, color=C_TEXT, zorder=4)

def draw_arrow(ax, x1, y1, x2, y2, text='', color=C_TEXT, ls='-', lw=1.35, text_offset=(0, 0.14), fontsize=9.5, ha='center', va='center', bidirectional=False):
    style = '<|-|>' if bidirectional else '-|>'
    arr = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=13,
                          linewidth=lw, linestyle=ls, color=color, zorder=2)
    ax.add_patch(arr)
    if text:
        mx, my = (x1 + x2)/2 + text_offset[0], (y1 + y2)/2 + text_offset[1]
        ax.text(mx, my, text, ha=ha, va=va, fontsize=fontsize, color=color, zorder=5)

# ==============================================================================
# HÌNH 2.1: MÔ HÌNH PUBLISH / SUBSCRIBE
# ==============================================================================
def make_hinh_2_1():
    fig, ax = plt.subplots(figsize=(9.2, 4.0), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.4)
    ax.axis('off')

    # Publisher
    draw_box(ax, 1.4, 2.2, 2.3, 1.45, "Publisher\n(Bên phát bản tin)", fc=C_NAVY_L, ec=C_NAVY, fontsize=11, fontweight='bold', tc=C_NAVY, rounding=0.08)

    # Broker outer
    broker_box = FancyBboxPatch((3.7, 0.45), 2.5, 3.5, boxstyle="round,pad=0,rounding_size=0.08",
                                facecolor=C_GRAY_L, edgecolor=C_SLATE, linewidth=1.6, zorder=1)
    ax.add_patch(broker_box)
    ax.text(4.95, 3.6, "MQTT Broker", ha='center', va='center', fontsize=11.5, fontweight='bold', color=C_TEXT)
    ax.text(4.95, 3.25, "(Quản lý kết nối & lọc theo Topic)", ha='center', va='center', fontsize=9.2, color=C_SLATE)
    draw_box(ax, 4.95, 2.4, 1.85, 0.65, "Topic A (dt42/cmd)", fc='#FFFFFF', ec=C_SLATE, fontsize=9.8, rounding=0.03)
    draw_box(ax, 4.95, 1.3, 1.85, 0.65, "Topic B (dt42/state)", fc='#FFFFFF', ec=C_SLATE, fontsize=9.8, rounding=0.03)

    # Subscribers
    draw_box(ax, 8.6, 3.2, 2.2, 1.15, "Subscriber 1\n(Đăng ký Topic A)", fc=C_GREEN_L, ec=C_GREEN, fontsize=10.5, fontweight='bold', tc=C_GREEN, rounding=0.08)
    draw_box(ax, 8.6, 1.1, 2.2, 1.15, "Subscriber 2\n(Đăng ký Topic A)", fc=C_GREEN_L, ec=C_GREEN, fontsize=10.5, fontweight='bold', tc=C_GREEN, rounding=0.08)

    # Arrows Publisher -> Broker
    draw_arrow(ax, 2.55, 2.2, 3.7, 2.2, "2. PUBLISH\n(Topic A, Payload)", color=C_NAVY, lw=1.5, text_offset=(0, 0.32), fontsize=9.5)

    # Subscriber 1 <-> Broker
    draw_arrow(ax, 7.5, 3.42, 6.2, 2.75, "1. SUBSCRIBE (Topic A)", color=C_SLATE, ls='--', lw=1.25, text_offset=(-0.15, 0.25), fontsize=9)
    draw_arrow(ax, 6.2, 2.45, 7.5, 3.05, "3. Chuyển tiếp PUBLISH", color=C_GREEN, lw=1.45, text_offset=(0.15, -0.25), fontsize=9.2)

    # Subscriber 2 <-> Broker
    draw_arrow(ax, 7.5, 1.32, 6.2, 2.05, "1. SUBSCRIBE (Topic A)", color=C_SLATE, ls='--', lw=1.25, text_offset=(0.18, 0.22), fontsize=9)
    draw_arrow(ax, 6.2, 1.75, 7.5, 0.95, "3. Chuyển tiếp PUBLISH", color=C_GREEN, lw=1.45, text_offset=(-0.12, -0.25), fontsize=9.2)

    plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(OUT_DIR, 'hinh_2_1_pubsub.png'), dpi=300)
    plt.close(fig)

# ==============================================================================
# HÌNH 2.2: TRÌNH TỰ GÓI TIN CỦA CÁC MỨC QoS
# ==============================================================================
def make_hinh_2_2():
    fig, ax = plt.subplots(figsize=(9.6, 4.3), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.2)
    ax.axis('off')

    panels = [
        ("QoS 0 (At most once)", 2.0),
        ("QoS 1 (At least once)", 6.0),
        ("QoS 2 (Exactly once)", 10.0)
    ]

    for title, cx in panels:
        ax.text(cx, 4.9, title, ha='center', va='center', fontsize=11, fontweight='bold', color=C_TEXT)
        x_s, x_r = cx - 1.15, cx + 1.15
        draw_box(ax, x_s, 4.3, 1.4, 0.52, "Bên gửi\n(Sender)", fc=C_NAVY_L, ec=C_NAVY, fontsize=9.2, fontweight='bold', tc=C_NAVY)
        draw_box(ax, x_r, 4.3, 1.4, 0.52, "Bên nhận\n(Receiver)", fc=C_GREEN_L, ec=C_GREEN, fontsize=9.2, fontweight='bold', tc=C_GREEN)
        ax.plot([x_s, x_s], [0.35, 4.04], ls='--', color='#64748B', lw=1.2, zorder=1)
        ax.plot([x_r, x_r], [0.35, 4.04], ls='--', color='#64748B', lw=1.2, zorder=1)

    # Dividers
    ax.plot([4.0, 4.0], [0.2, 5.05], color='#CBD5E1', lw=1.1)
    ax.plot([8.0, 8.0], [0.2, 5.05], color='#CBD5E1', lw=1.1)

    # QoS 0
    draw_arrow(ax, 0.85, 3.55, 3.15, 3.2, "1. PUBLISH (QoS=0)", color=C_NAVY, lw=1.4, text_offset=(0, 0.22), fontsize=9.2)
    ax.text(2.0, 2.45, "(Không có gói xác nhận;\ngửi tối đa 1 lần)", ha='center', va='center', fontsize=8.8, style='italic', color=C_SLATE)

    # QoS 1
    draw_arrow(ax, 4.85, 3.55, 7.15, 3.2, "1. PUBLISH (QoS=1, PacketId)", color=C_NAVY, lw=1.4, text_offset=(0, 0.22), fontsize=9.0)
    draw_arrow(ax, 7.15, 2.45, 4.85, 2.1, "2. PUBACK (PacketId)", color=C_GREEN, ls='--', lw=1.4, text_offset=(0, 0.22), fontsize=9.0)
    ax.text(6.0, 1.4, "(Xác nhận 2 bước;\nnhận ít nhất 1 lần)", ha='center', va='center', fontsize=8.8, style='italic', color=C_SLATE)

    # QoS 2
    draw_arrow(ax, 8.85, 3.65, 11.15, 3.35, "1. PUBLISH (QoS=2, PacketId)", color=C_NAVY, lw=1.4, text_offset=(0, 0.2), fontsize=8.8)
    draw_arrow(ax, 11.15, 2.85, 8.85, 2.55, "2. PUBREC (PacketId)", color=C_GREEN, ls='--', lw=1.4, text_offset=(0, 0.2), fontsize=8.8)
    draw_arrow(ax, 8.85, 2.0, 11.15, 1.7, "3. PUBREL (PacketId)", color=C_NAVY, lw=1.4, text_offset=(0, 0.2), fontsize=8.8)
    draw_arrow(ax, 11.15, 1.15, 8.85, 0.85, "4. PUBCOMP (PacketId)", color=C_GREEN, ls='--', lw=1.4, text_offset=(0, 0.2), fontsize=8.8)
    ax.text(10.0, 0.38, "(Bắt tay 4 bước; đúng 1 lần)", ha='center', va='center', fontsize=8.8, style='italic', color=C_SLATE)

    plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(OUT_DIR, 'hinh_2_2_qos.png'), dpi=300)
    plt.close(fig)

# ==============================================================================
# HÌNH 3.1: SƠ ĐỒ KHỐI HỆ THỐNG (ĐẦY ĐỦ 3 TOPIC: dt42/cmd, dt42/state, dt42/status)
# ==============================================================================
def make_hinh_3_1():
    fig, ax = plt.subplots(figsize=(9.8, 4.6), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5.2)
    ax.axis('off')

    # Người dùng & Nút nhấn
    ax.text(1.75, 4.88, "Người dùng (Trình duyệt Web)", ha='center', va='center', fontsize=10, fontweight='bold', color=C_TEXT)
    draw_arrow(ax, 1.75, 4.68, 1.75, 4.18, "", color=C_TEXT, bidirectional=True)

    ax.text(9.25, 4.88, "Nút nhấn tại chỗ (GPIO27)", ha='center', va='center', fontsize=10, fontweight='bold', color=C_TEXT)
    draw_arrow(ax, 9.25, 4.68, 9.25, 4.18, "", color=C_TEXT)

    # 3 Main Blocks
    blocks = [
        (1.75, 2.45, 3.0, 3.4, C_NAVY_L, C_NAVY, "GIAO DIỆN ĐIỀU KHIỂN", "(Web Dashboard - MQTT.js)", C_NAVY, [
            "• Phát lệnh Bật/Tắt kèm cmd_id, t_send",
            "• Nhận phản hồi trạng thái thực tế",
            "• Đối chiếu cmd_id và tính RTT",
            "• Giám sát kết nối thiết bị (LWT)"
        ]),
        (5.5, 2.45, 2.8, 3.4, C_GRAY_L, C_SLATE, "TRUNG TÂM CHUYỂN TIẾP", "(EMQX MQTT Broker)", C_TEXT, [
            "• Quản lý phiên TCP & WebSocket",
            "• Định tuyến bản tin theo Topic",
            "• Thực thi bắt tay QoS 0 / 1 / 2",
            "• Lưu bản tin Retain & phát LWT"
        ]),
        (9.25, 2.45, 3.0, 3.4, C_GREEN_L, C_GREEN, "KHỐI CHẤP HÀNH", "(ESP32-WROOM-32 & Relay)", C_GREEN, [
            "• Giải mã lệnh JSON từ dt42/cmd",
            "• Kích đóng/ngắt Relay (GPIO26)",
            "• Quét nút nhấn chống dội 50 ms",
            "• Đọc chân GPIO26 & gửi phản hồi"
        ])
    ]

    for x, y, w, h, fc, ec, title, sub, tc, bullets in blocks:
        box = FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                             facecolor=fc, edgecolor=ec, linewidth=1.6, zorder=2)
        ax.add_patch(box)
        ax.text(x, y + h/2 - 0.35, title, ha='center', va='center', fontsize=10.5, fontweight='bold', color=tc)
        ax.text(x, y + h/2 - 0.68, sub, ha='center', va='center', fontsize=9.2, color=C_SLATE)
        for idx, b in enumerate(bullets):
            ax.text(x - w/2 + 0.16, y + 0.42 - idx*0.48, b, ha='left', va='center', fontsize=9.0, color=C_TEXT)

    # Arrows Web <-> Broker
    draw_arrow(ax, 3.25, 3.15, 4.1, 3.15, "dt42/cmd", color=C_NAVY, lw=1.5, text_offset=(0, 0.20), fontsize=9.2)
    draw_arrow(ax, 4.1, 2.35, 3.25, 2.35, "dt42/state [Retain]", color=C_GREEN, ls='--', lw=1.5, text_offset=(0, 0.20), fontsize=8.8)
    draw_arrow(ax, 4.1, 1.55, 3.25, 1.55, "dt42/status [LWT]", color=C_AMBER, ls='-.', lw=1.35, text_offset=(0, 0.20), fontsize=8.8)
    ax.text(3.675, 0.92, "WebSocket (:8083/mqtt)", ha='center', va='center', fontsize=8.8, style='italic', color=C_SLATE)

    # Arrows Broker <-> ESP32
    draw_arrow(ax, 6.9, 3.15, 7.75, 3.15, "dt42/cmd", color=C_NAVY, lw=1.5, text_offset=(0, 0.20), fontsize=9.2)
    draw_arrow(ax, 7.75, 2.35, 6.9, 2.35, "dt42/state [Retain]", color=C_GREEN, ls='--', lw=1.5, text_offset=(0, 0.20), fontsize=8.8)
    draw_arrow(ax, 7.75, 1.55, 6.9, 1.55, "dt42/status [LWT]", color=C_AMBER, ls='-.', lw=1.35, text_offset=(0, 0.20), fontsize=8.8)
    ax.text(7.325, 0.92, "TCP/IP Wi-Fi (:1883)", ha='center', va='center', fontsize=8.8, style='italic', color=C_SLATE)

    # Legend at bottom
    draw_arrow(ax, 1.2, 0.3, 2.1, 0.3, "", color=C_NAVY, lw=1.5)
    ax.text(2.2, 0.3, "Lệnh điều khiển (dt42/cmd)", ha='left', va='center', fontsize=9)
    draw_arrow(ax, 4.6, 0.3, 5.5, 0.3, "", color=C_GREEN, ls='--', lw=1.5)
    ax.text(5.6, 0.3, "Phản hồi trạng thái (dt42/state)", ha='left', va='center', fontsize=9)
    draw_arrow(ax, 8.1, 0.3, 9.0, 0.3, "", color=C_AMBER, ls='-.', lw=1.35)
    ax.text(9.1, 0.3, "Trạng thái kết nối (dt42/status)", ha='left', va='center', fontsize=9)

    plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(OUT_DIR, 'hinh_3_1_so_do_khoi.png'), dpi=300)
    plt.close(fig)

# ==============================================================================
# HÌNH 3.2: TRÌNH TỰ XỬ LÝ MỘT LỆNH ĐIỀU KHIỂN (ĐỒNG BỘ 4 BƯỚC CHÍNH & CHI TIẾT CHẶNG)
# ==============================================================================
def make_hinh_3_2():
    fig, ax = plt.subplots(figsize=(9.4, 4.8), dpi=300)
    ax.set_xlim(0, 10.5)
    ax.set_ylim(0, 5.6)
    ax.axis('off')

    lifelines = [
        (2.3, "Web Dashboard\n(MQTT.js Client)", C_NAVY_L, C_NAVY),
        (5.5, "EMQX Broker\n(WS :8083 / TCP :1883)", C_GRAY_L, C_SLATE),
        (8.7, "ESP32 & Relay\n(GPIO26 / GPIO27)", C_GREEN_L, C_GREEN)
    ]

    for x, label, fc, ec in lifelines:
        draw_box(ax, x, 5.1, 2.3, 0.62, label, fc=fc, ec=ec, fontsize=9.8, fontweight='bold', tc=ec)
        ax.plot([x, x], [0.25, 4.79], ls='--', color='#64748B', lw=1.2, zorder=1)

    # Bước 1: Phát lệnh tại t_send
    y1 = 4.25
    ax.plot([0.5, 2.3], [y1, y1], ls=':', color=C_NAVY, lw=1.2)
    ax.text(0.45, y1 + 0.14, "$t_{\\mathrm{send}}$", ha='left', va='bottom', fontsize=10.5, fontweight='bold', color=C_NAVY)

    draw_arrow(ax, 2.3, y1, 5.5, 4.0, "Bước 1a: PUBLISH dt42/cmd", color=C_NAVY, lw=1.45, text_offset=(0, 0.20), fontsize=9.2)
    ax.text(3.9, 3.84, '{"action":"ON", "cmd_id":k, "t_send":$t_{\\mathrm{send}}$}', ha='center', va='top', fontsize=8.4, style='italic', color=C_SLATE)

    draw_arrow(ax, 5.5, 3.55, 8.7, 3.3, "Bước 1b: Chuyển tiếp dt42/cmd", color=C_NAVY, lw=1.45, text_offset=(0, 0.20), fontsize=9.2)

    # Bước 2: Thực thi tại ESP32
    draw_box(ax, 8.7, 2.65, 2.5, 0.68, "Bước 2: Giải mã JSON, kích GPIO26\nĐọc lại digitalRead(GPIO26)", fc='#FFFFFF', ec=C_GREEN, fontsize=8.8)

    # Bước 3: Phát phản hồi trạng thái
    draw_arrow(ax, 8.7, 2.0, 5.5, 1.75, "Bước 3a: PUBLISH dt42/state [Retain]", color=C_GREEN, ls='--', lw=1.45, text_offset=(0, 0.20), fontsize=9.2)
    ax.text(7.1, 1.58, '{"state":"ON", "cmd_id":k, "t_send":$t_{\\mathrm{send}}$}', ha='center', va='top', fontsize=8.4, style='italic', color=C_SLATE)

    y_ack = 1.15
    draw_arrow(ax, 5.5, 1.4, 2.3, y_ack, "Bước 3b: Chuyển tiếp dt42/state", color=C_GREEN, ls='--', lw=1.45, text_offset=(0, 0.20), fontsize=9.2)

    # Bước 4: Nhận phản hồi tại t_ack và tính RTT
    ax.plot([0.5, 2.3], [y_ack, y_ack], ls=':', color=C_NAVY, lw=1.2)
    ax.text(0.45, y_ack + 0.14, "$t_{\\mathrm{ack}}$", ha='left', va='bottom', fontsize=10.5, fontweight='bold', color=C_NAVY)

    # Mũi tên đo RTT
    draw_arrow(ax, 1.15, y_ack, 1.15, y1, "", color=C_NAVY, lw=1.4, bidirectional=True)
    ax.text(1.05, (y1 + y_ack)/2, "$\\mathrm{RTT} = t_{\\mathrm{ack}} - t_{\\mathrm{send}}$", ha='right', va='center', fontsize=9.8, fontweight='bold', color=C_NAVY,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFFFFF', edgecolor=C_NAVY, lw=0.8))

    draw_box(ax, 2.3, 0.55, 2.7, 0.64, "Bước 4: Cập nhật giao diện ON/OFF\nĐối chiếu cmd_id == k & tính RTT", fc='#FFFFFF', ec=C_NAVY, fontsize=8.8)

    plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(OUT_DIR, 'hinh_3_2_trinh_tu.png'), dpi=300)
    plt.close(fig)

# ==============================================================================
# HÌNH 3.3: LƯU ĐỒ THUẬT TOÁN TRÊN ESP32 (CHUẨN ISO 5807)
# ==============================================================================
def make_hinh_3_3():
    fig, ax = plt.subplots(figsize=(8.6, 7.2), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9.6)
    ax.axis('off')

    cx = 3.2
    rx = 7.4

    draw_oval(ax, cx, 9.1, 2.3, 0.52, "Bắt đầu")
    draw_arrow(ax, cx, 8.84, cx, 8.42)

    draw_box(ax, cx, 8.02, 4.4, 0.78, "Khởi tạo GPIO26 (OUTPUT, LOW), GPIO27 (INPUT_PULLUP)\nKết nối Wi-Fi & MQTT Broker (khai báo LWT dt42/status)", fc='#FFFFFF', ec=C_SLATE, fontsize=9.2)
    draw_arrow(ax, cx, 7.63, cx, 7.22)

    draw_parallelogram(ax, cx, 6.82, 4.4, 0.78, "Publish dt42/status {\"online\":true} [Retain]\nSubscribe dt42/cmd; đồng bộ dt42/state ban đầu", fc=C_GREEN_L, ec=C_GREEN, fontsize=9.0)
    draw_arrow(ax, cx, 6.43, cx, 5.95)

    # Điểm nhập vòng lặp loop()
    ax.plot(cx, 5.8, 'o', color=C_TEXT, markersize=4.5, zorder=5)
    draw_arrow(ax, cx, 5.8, cx, 5.42)

    # Kiểm tra kết nối
    draw_diamond(ax, cx, 4.82, 3.6, 1.15, "client.connected()\nduy trì?", fc='#FFFFFF', ec=C_SLATE, fontsize=9.2)
    ax.text(cx - 2.0, 5.02, "Không", fontsize=8.8, style='italic', color=C_RED)
    # Nhánh kết nối lại
    ax.plot([cx - 1.8, 0.55, 0.55, cx], [4.82, 4.82, 8.02, 8.02], color=C_SLATE, lw=1.25)
    draw_arrow(ax, 0.85, 8.02, cx - 2.2, 8.02, "", color=C_SLATE)

    ax.text(cx + 0.18, 4.08, "Có", fontsize=8.8, style='italic', color=C_GREEN)
    draw_arrow(ax, cx, 4.24, cx, 3.72)

    # Nhánh 1: Nhận bản tin dt42/cmd?
    draw_diamond(ax, cx, 3.1, 3.7, 1.2, "Nhận bản tin\ntrên dt42/cmd?", fc='#FFFFFF', ec=C_SLATE, fontsize=9.2)
    draw_arrow(ax, cx + 1.85, 3.1, rx - 1.75, 3.1, "Có", text_offset=(0, 0.18), fontsize=9.0)
    draw_box(ax, rx, 3.1, 3.5, 0.82, "Giải mã action, cmd_id, t_send\nGhi mức logic ra chân GPIO26", fc=C_NAVY_L, ec=C_NAVY, fontsize=9.0)

    ax.text(cx + 0.18, 2.32, "Không", fontsize=8.8, style='italic', color=C_SLATE)
    draw_arrow(ax, cx, 2.5, cx, 1.98)

    # Nhánh 2: Nút nhấn tại chỗ?
    draw_diamond(ax, cx, 1.38, 3.7, 1.2, "Nhấn nút GPIO27\n(chống dội 50 ms)?", fc='#FFFFFF', ec=C_SLATE, fontsize=9.2)
    draw_arrow(ax, cx + 1.85, 1.38, rx - 1.75, 1.38, "Có", text_offset=(0, 0.18), fontsize=9.0)
    draw_box(ax, rx, 1.38, 3.5, 0.82, "Đảo trạng thái chân GPIO26\nGán cmd_id = 0, t_send = 0", fc=C_NAVY_L, ec=C_NAVY, fontsize=9.0)

    # Hợp nhánh xử lý phản hồi bên phải
    ax.plot([rx + 1.75, 9.55, 9.55], [3.1, 3.1, 1.38], color=C_TEXT, lw=1.3)
    ax.plot([rx + 1.75, 9.55], [1.38, 1.38], color=C_TEXT, lw=1.3)
    ax.plot([9.55, 9.55], [1.38, 0.42], color=C_TEXT, lw=1.3)
    draw_arrow(ax, 9.55, 0.42, rx + 1.85, 0.42)

    draw_parallelogram(ax, rx, 0.42, 3.7, 0.72, "Đọc digitalRead(GPIO26)\nPublish dt42/state [Retain]", fc=C_GREEN_L, ec=C_GREEN, fontsize=9.0)

    # Đường hồi tiếp về đầu vòng lặp
    ax.text(cx + 0.18, 0.58, "Không", fontsize=8.8, style='italic', color=C_SLATE)
    ax.plot([cx, cx], [0.78, 0.42], color=C_TEXT, lw=1.3)
    ax.plot([rx - 1.85, 0.25, 0.25, cx], [0.42, 0.42, 5.8, 5.8], color=C_TEXT, lw=1.3)
    draw_arrow(ax, 1.5, 5.8, cx, 5.8)

    plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(OUT_DIR, 'hinh_3_3_luu_do_esp32.png'), dpi=300)
    plt.close(fig)

# ==============================================================================
# HÌNH 3.4: LƯU ĐỒ THUẬT TOÁN TRÊN WEB DASHBOARD (CHUẨN ISO 5807)
# ==============================================================================
def make_hinh_3_4():
    fig, ax = plt.subplots(figsize=(9.0, 7.6), dpi=300)
    ax.set_xlim(0, 10.4)
    ax.set_ylim(0, 10.2)
    ax.axis('off')

    cx = 3.1
    rx = 7.6

    draw_oval(ax, cx, 9.7, 2.3, 0.52, "Bắt đầu")
    draw_arrow(ax, cx, 9.44, cx, 9.05)

    draw_parallelogram(ax, cx, 8.65, 4.5, 0.75, "Kết nối Broker qua WebSocket (:8083/mqtt)\nSubscribe dt42/state, dt42/status", fc=C_GREEN_L, ec=C_GREEN, fontsize=9.2)
    draw_arrow(ax, cx, 8.27, cx, 7.82)

    # Điểm vòng lặp sự kiện
    ax.plot(cx, 7.72, 'o', color=C_TEXT, markersize=4.5, zorder=5)
    draw_arrow(ax, cx, 7.72, cx, 7.35)

    # Sự kiện 1: Nhận dt42/status?
    draw_diamond(ax, cx, 6.75, 3.7, 1.15, "Nhận bản tin\ntrên dt42/status?", fc='#FFFFFF', ec=C_SLATE, fontsize=9.2)
    draw_arrow(ax, cx + 1.85, 6.75, rx - 1.85, 6.75, "Có", text_offset=(0, 0.18), fontsize=9.0)
    draw_box(ax, rx, 6.75, 3.7, 0.82, "Cập nhật trạng thái kết nối ESP32\nKhóa nút Bật/Tắt nếu online == false", fc=C_AMBER_L, ec=C_AMBER, fontsize=8.8)

    ax.text(cx + 0.18, 5.98, "Không", fontsize=8.8, style='italic', color=C_SLATE)
    draw_arrow(ax, cx, 6.17, cx, 5.65)

    # Sự kiện 2: Người dùng nhấn nút Bật/Tắt?
    draw_diamond(ax, cx, 5.05, 3.7, 1.15, "Nhấn nút Bật/Tắt\n(khi ESP32 Online)?", fc='#FFFFFF', ec=C_SLATE, fontsize=9.2)
    draw_arrow(ax, cx + 1.85, 5.05, rx - 1.85, 5.05, "Có", text_offset=(0, 0.18), fontsize=9.0)
    draw_parallelogram(ax, rx, 5.05, 3.7, 0.85, "Tăng cmd_id; ghi t_send hiện tại\nLưu pending_cmd_id = cmd_id\nPublish dt42/cmd {action, cmd_id, t_send}", fc=C_NAVY_L, ec=C_NAVY, fontsize=8.6)

    ax.text(cx + 0.18, 4.28, "Không", fontsize=8.8, style='italic', color=C_SLATE)
    draw_arrow(ax, cx, 4.47, cx, 3.92)

    # Sự kiện 3: Nhận bản tin dt42/state?
    draw_diamond(ax, cx, 3.32, 3.7, 1.15, "Nhận bản tin\ntrên dt42/state?", fc='#FFFFFF', ec=C_SLATE, fontsize=9.2)
    draw_arrow(ax, cx + 1.85, 3.32, rx - 1.85, 3.32, "Có", text_offset=(0, 0.18), fontsize=9.0)
    draw_box(ax, rx, 3.32, 3.7, 0.78, "Ghi nhận thời điểm t_ack\nCập nhật hiển thị Relay (ON / OFF)", fc='#FFFFFF', ec=C_NAVY, fontsize=9.0)
    draw_arrow(ax, rx, 2.93, rx, 2.45)

    # Kiểm tra phiên lệnh hợp lệ để tính RTT
    draw_diamond(ax, rx, 1.82, 3.9, 1.22, "t_send > 0 VÀ\ncmd_id == pending_cmd_id?", fc='#FFFFFF', ec=C_SLATE, fontsize=8.8)
    draw_arrow(ax, rx, 1.21, rx, 0.82, "Có", text_offset=(0.25, 0), fontsize=9.0)

    draw_box(ax, rx, 0.45, 3.7, 0.72, "Tính RTT = t_ack - t_send; lưu thống kê\nXóa cờ pending_cmd_id = null", fc=C_GREEN_L, ec=C_GREEN, fontsize=8.8)

    # Đường gom về vòng lặp sự kiện
    ax.plot([rx + 1.85, 10.05], [6.75, 6.75], color=C_TEXT, lw=1.25)
    ax.plot([rx + 1.85, 10.05], [5.05, 5.05], color=C_TEXT, lw=1.25)
    ax.plot([rx + 1.95, 10.05], [1.82, 1.82], color=C_TEXT, lw=1.25)
    ax.text(rx + 2.02, 1.98, "Không", fontsize=8.6, style='italic', color=C_SLATE)
    ax.plot([rx + 1.85, 10.05], [0.45, 0.45], color=C_TEXT, lw=1.25)
    ax.plot([10.05, 10.05, 0.35, 0.35, cx], [6.75, 0.12, 0.12, 7.72, 7.72], color=C_TEXT, lw=1.25)

    ax.text(cx + 0.18, 2.52, "Không", fontsize=8.8, style='italic', color=C_SLATE)
    ax.plot([cx, cx], [2.74, 0.12], color=C_TEXT, lw=1.25)
    draw_arrow(ax, 1.5, 7.72, cx, 7.72)

    plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(OUT_DIR, 'hinh_3_4_luu_do_web.png'), dpi=300)
    plt.close(fig)

# ==============================================================================
# HÌNH 4.1: SƠ ĐỒ ĐẤU NỐI PHẦN CỨNG VÀ KẾT NỐI MẠNG THỰC NGHIỆM
# ==============================================================================
def make_hinh_4_1():
    fig, ax = plt.subplots(figsize=(9.8, 4.9), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5.4)
    ax.axis('off')

    # Hàng trên: Kết nối mạng
    draw_box(ax, 1.8, 4.45, 2.7, 1.1, "Máy tính điều khiển\n(Web Dashboard)", subtext="Trình duyệt + MQTT.js", fc=C_NAVY_L, ec=C_NAVY, fontsize=10, tc=C_NAVY)
    draw_box(ax, 5.5, 4.45, 2.7, 1.1, "EMQX MQTT Broker\n(Máy chủ cục bộ)", subtext="TCP :1883 | WS :8083/mqtt", fc=C_GRAY_L, ec=C_SLATE, fontsize=10, tc=C_TEXT)
    draw_box(ax, 9.2, 4.45, 2.6, 1.1, "Bộ định tuyến Wi-Fi\n(Access Point 2.4 GHz)", subtext="IEEE 802.11n (LAN)", fc='#FFFFFF', ec=C_SLATE, fontsize=10, tc=C_TEXT)

    draw_arrow(ax, 3.15, 4.45, 4.15, 4.45, "WebSocket\n(:8083)", color=C_NAVY, lw=1.4, text_offset=(0, 0.28), fontsize=8.8, bidirectional=True)
    draw_arrow(ax, 6.85, 4.45, 7.9, 4.45, "TCP/IP\n(:1883)", color=C_SLATE, lw=1.4, text_offset=(0, 0.28), fontsize=8.8, bidirectional=True)
    draw_arrow(ax, 9.2, 3.9, 9.2, 3.15, "Wi-Fi 2.4 GHz", color=C_GREEN, ls='--', lw=1.4, text_offset=(0.68, 0), fontsize=9.0, bidirectional=True)

    # Khối Vi điều khiển ESP32-WROOM-32
    esp_box = FancyBboxPatch((6.8, 1.55), 3.7, 1.55, boxstyle="round,pad=0,rounding_size=0.06",
                             facecolor=C_GREEN_L, edgecolor=C_GREEN, linewidth=1.6, zorder=2)
    ax.add_patch(esp_box)
    ax.text(8.65, 2.82, "Vi điều khiển ESP32-WROOM-32", ha='center', va='center', fontsize=10.5, fontweight='bold', color=C_GREEN)
    ax.text(6.95, 2.38, "• GPIO27 (INPUT_PULLUP)", ha='left', va='center', fontsize=9.0, color=C_TEXT)
    ax.text(6.95, 2.02, "• GPIO26 (OUTPUT Control)", ha='left', va='center', fontsize=9.0, color=C_TEXT)
    ax.text(6.95, 1.70, "• VIN (5V DC) & GND", ha='left', va='center', fontsize=9.0, color=C_TEXT)

    # Nút nhấn tại chỗ
    draw_box(ax, 3.6, 2.35, 2.6, 1.0, "Nút nhấn tại chỗ\n(Tactile Push Button)", subtext="Chân 1 → GPIO27 | Chân 2 → GND", fc='#FFFFFF', ec=C_SLATE, fontsize=9.5)
    draw_arrow(ax, 4.9, 2.48, 6.8, 2.48, "Tín hiệu nút nhấn (GPIO27)", color=C_SLATE, lw=1.35, text_offset=(0, 0.18), fontsize=8.8)
    ax.plot([4.9, 6.8], [2.15, 2.15], color='#475569', ls=':', lw=1.2)
    ax.text(5.85, 1.98, "Dây chung GND", ha='center', va='center', fontsize=8.4, color=C_SLATE)

    # Module Relay 1 kênh 5V
    draw_box(ax, 8.65, 0.58, 3.7, 0.92, "Module Relay 1 kênh 5V DC (Cách ly Opto)", subtext="Ngõ điều khiển: VCC (5V), GND, IN ← GPIO26", fc=C_AMBER_L, ec=C_AMBER, fontsize=9.5, tc=C_AMBER)
    draw_arrow(ax, 8.65, 1.55, 8.65, 1.04, "GPIO26 → IN (Mức HIGH đóng NO)", color=C_AMBER, lw=1.45, text_offset=(1.32, 0), fontsize=8.8)

    # Mạch công suất / Thiết bị tải
    draw_box(ax, 4.5, 0.58, 2.4, 0.92, "Thiết bị tải\n(Đèn / Phụ tải thực nghiệm)", subtext="Đóng ngắt qua tiếp điểm NO", fc='#FFFFFF', ec=C_SLATE, fontsize=9.5)
    draw_box(ax, 1.3, 0.58, 2.1, 0.92, "Nguồn cấp tải\n(DC / AC)", subtext="Cấp nguồn mạch tải", fc='#FFFFFF', ec=C_SLATE, fontsize=9.5)

    draw_arrow(ax, 6.8, 0.58, 5.7, 0.58, "Tiếp điểm\nCOM – NO", color=C_RED, lw=1.5, text_offset=(0, 0.25), fontsize=8.8)
    ax.plot([2.35, 3.3], [0.58, 0.58], color=C_RED, lw=1.5)
    ax.text(2.82, 0.82, "Mạch tải", ha='center', va='center', fontsize=8.8, color=C_RED)

    plt.tight_layout(pad=0.2)
    plt.savefig(os.path.join(OUT_DIR, 'hinh_4_1_so_do_lap_rap.png'), dpi=300)
    plt.close(fig)

# ==============================================================================
# HÌNH 4.2: BIỂU ĐỒ KẾT QUẢ ĐO RTT 30 LỆNH THEO BA MỨC QoS
# ==============================================================================
def make_hinh_4_2():
    with open(r'C:\Users\Admin\Documents\GitHub\mttqx\benchmark\results.json', 'r', encoding='utf-8') as f:
        res = json.load(f)

    s0 = res['rawSamples']['0']
    s1 = res['rawSamples']['1']
    s2 = res['rawSamples']['2']
    trials = np.arange(1, 31)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.8, 4.0), dpi=300, gridspec_kw={'width_ratios': [1.65, 1.0]})

    # Panel (a): Chuỗi 30 lần đo
    ax1.plot(trials, s0, marker='o', markersize=4, lw=1.4, color='#1B365D', label=f"QoS 0 (TB = {np.mean(s0):.2f} ms)")
    ax1.plot(trials, s1, marker='s', markersize=4, lw=1.4, color='#1E5631', label=f"QoS 1 (TB = {np.mean(s1):.2f} ms)")
    ax1.plot(trials, s2, marker='^', markersize=4.5, lw=1.4, color='#8B1E1E', label=f"QoS 2 (TB = {np.mean(s2):.2f} ms)")

    ax1.set_title("(a) Độ trễ RTT qua 30 lần đo liên tiếp", fontsize=10.5, fontweight='bold', pad=8)
    ax1.set_xlabel("Lần đo thứ i (1 ≤ i ≤ 30)", fontsize=10)
    ax1.set_ylabel("Độ trễ khứ hồi RTT (ms)", fontsize=10)
    ax1.set_xlim(0.5, 30.5)
    ax1.set_ylim(10, 48)
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend(loc='upper right', fontsize=8.8, frameon=True)

    # Panel (b): Phân bố thống kê Box-plot + Mean
    bp = ax2.boxplot([s0, s1, s2], tick_labels=['QoS 0', 'QoS 1', 'QoS 2'], patch_artist=True, widths=0.45,
                     boxprops=dict(linewidth=1.2), medianprops=dict(color='#111827', linewidth=1.6),
                     whiskerprops=dict(linewidth=1.2), capprops=dict(linewidth=1.2))
    colors = [C_NAVY_L, C_GREEN_L, '#FEE2E2']
    edges  = [C_NAVY, C_GREEN, C_RED]
    for patch, fc, ec in zip(bp['boxes'], colors, edges):
        patch.set_facecolor(fc)
        patch.set_edgecolor(ec)

    means = [np.mean(s0), np.mean(s1), np.mean(s2)]
    stds  = [np.std(s0, ddof=1), np.std(s1, ddof=1), np.std(s2, ddof=1)]
    ax2.scatter([1, 2, 3], means, color=edges, zorder=5, s=30, marker='D', label='Giá trị TB (Mean)')
    for idx, (m, sd) in enumerate(zip(means, stds), start=1):
        ax2.text(idx, m + sd + 1.8, f"{m:.2f}±{sd:.2f}", ha='center', va='bottom', fontsize=8.6, fontweight='bold', color=edges[idx-1])

    ax2.set_title("(b) Phân bố thống kê RTT theo mức QoS", fontsize=10.5, fontweight='bold', pad=8)
    ax2.set_ylabel("Độ trễ khứ hồi RTT (ms)", fontsize=10)
    ax2.set_ylim(10, 48)
    ax2.grid(True, axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout(pad=0.4)
    plt.savefig(os.path.join(OUT_DIR, 'hinh_4_2_bieu_do_rtt.png'), dpi=300)
    plt.close(fig)

if __name__ == '__main__':
    make_hinh_2_1()
    make_hinh_2_2()
    make_hinh_3_1()
    make_hinh_3_2()
    make_hinh_3_3()
    make_hinh_3_4()
    make_hinh_4_1()
    make_hinh_4_2()
    print("Generated all 8 figures successfully in", OUT_DIR)
