# Server.py — PC 端多设备 TCP 服务器
# 功能：管理多个 ESP32 设备连接，JSON 协议通信，CLI 交互控制

import socket
import threading
import json
import time

# ==================== 服务器配置 ====================

LISTEN_IP = '0.0.0.0'
LISTEN_PORT = 8888

# ==================== 全局设备注册表 ====================
_devices = {}          # { box_id: {"conn": ..., "addr": ..., "status": ..., "last_seen": ...} }
_devices_lock = threading.Lock()
_current_box = None   # 当前控制的设备 box_id


# ==================== 设备处理器 ====================

def handle_client(conn, addr):
    global _current_box
    # 注册设备，等收到 register 消息才知道 box_id
    buf = b""
    _box_id = None

    while True:
        try:
            raw = conn.recv(512)
            if not raw:
                break
            buf += raw

            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line.decode('utf-8'))
                except:
                    continue

                msg_type = msg.get("type")

                # 首次收到 register 消息时正式注册
                if msg_type == "register" and _box_id is None:
                    _box_id = msg.get("box_id", f"{addr[0]}:{addr[1]}")
                    with _devices_lock:
                        _devices[_box_id] = {
                            "conn": conn,
                            "addr": addr,
                            "status": {"led": 0, "light": 0, "pir": 0, "mode": "-"},
                            "last_seen": time.time()
                        }
                        if _current_box is None:
                            _current_box = _box_id
                    print(f"[Server]AI智能终端盒子上线: {_box_id}  Addr:{addr}")

                # 手动 status 查询回复 — 显示详情
                elif msg_type == "status" and _box_id:
                    with _devices_lock:
                        if _box_id in _devices:
                            _devices[_box_id]["status"] = msg
                            _devices[_box_id]["last_seen"] = time.time()
                    led = msg.get("led")
                    light = msg.get("light")
                    pir = msg.get("pir")
                    mode = msg.get("mode", "?")
                    print(f"\n{'='*50}")
                    print(f"  设备: {_box_id}")
                    print(f"  LED   : {'ON' if led else 'OFF'}")
                    print(f"  光敏  : {'Dark(暗)' if light else 'Bright(亮)'} (值={light})")
                    print(f"  人体  : {'Body(有人)' if pir else 'None(无人)'} (值={pir})")
                    print(f"  模式  : {'自动' if mode == 'auto' else '手动'}")
                    print(f"{'='*50}")

                # 周期心跳 — 静默更新缓存
                elif msg_type == "heartbeat" and _box_id:
                    with _devices_lock:
                        if _box_id in _devices:
                            _devices[_box_id]["status"] = msg
                            _devices[_box_id]["last_seen"] = time.time()

                # 命令确认
                elif msg_type == "ack" and _box_id:
                    cmd = msg.get("cmd")
                    result = msg.get("result")
                    reason = msg.get("reason", "")
                    if result == "ok":
                        print(f"[{_box_id}] {cmd} -> OK")
                    else:
                        print(f"[{_box_id}] {cmd} -> ERR: {reason}")

                # 信息查询回复
                elif msg_type == "info" and _box_id:
                    cmd = msg.get("cmd")
                    data = msg.get("data", {})
                    if cmd == "light":
                        print(f"[{_box_id}] 光敏: {data.get('text')} (值={data.get('value')})")
                    elif cmd == "human":
                        print(f"[{_box_id}] 人体: {data.get('text')} (值={data.get('value')})")
                    elif cmd == "sensor":
                        print(f"[{_box_id}] 光敏={data.get('light')} 人体={data.get('pir')}")
                    elif cmd == "ip":
                        print(f"[{_box_id}] 设备IP={data.get('device_ip')} 服务器IP={data.get('server_ip')}")
                    elif cmd == "box_id":
                        print(f"[{_box_id}] Box_ID={data.get('box_id')}")
                    elif cmd == "help":
                        cmds = data.get("commands", [])
                        print(f"[{_box_id}] 支持指令: {'/'.join(cmds)}")
                    else:
                        print(f"[{_box_id}] {data}")

        except Exception as e:
            print(f"[{_box_id or addr}] 连接异常: {e}")
            break

    # 清理
    with _devices_lock:
        if _box_id and _box_id in _devices:
            del _devices[_box_id]
        if _current_box == _box_id:
            keys = list(_devices.keys())
            _current_box = keys[0] if keys else None
    conn.close()
    print(f"[Server]设备断开: {_box_id or addr}")


def send_command(box_id, cmd):
    with _devices_lock:
        device = _devices.get(box_id)

    if not device:
        print(f"[Server]设备 {box_id} 不存在")
        return

    line = json.dumps(cmd) + "\n"
    try:
        device["conn"].sendall(line.encode('utf-8'))
    except Exception as e:
        print(f"[Server]发送失败: {e}")


# ==================== 服务器主逻辑 ====================

def accept_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    sock.listen(10)
    print(f"[Server]Tcp服务器启动，监听 {LISTEN_IP}:{LISTEN_PORT}，等待AI智能终端盒子连接...")

    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


def cli_loop():
    global _current_box

    print("\n—— 手动控制 ——          —— 查询 ——        —— 屏幕 ——           —— 系统 ——")
    print("on      开灯              status  全部状态    screen_on   亮屏      switch <名称>")
    print("off     关灯              light   光敏        screen_off  息屏      list  设备列表")
    print("auto    自动模式          human   人体        screen_invert 反色    help  指令列表")
    print("manual  手动模式          sensor  全部传感器  screen_normal 恢复    exit  退出")
    print("                          ip      网络信息    contrast:<值> 对比度")
    print("                          box_id  设备ID")
    while True:
        try:
            user_cmd = input("请输入指令：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Server]退出")
            break

        if not user_cmd:
            continue

        cmd_lower = user_cmd.lower()

        # 切换设备
        if cmd_lower.startswith("switch "):
            target = user_cmd.split(" ", 1)[1]
            with _devices_lock:
                if target in _devices:
                    _current_box = target
                    print(f"当前设备: {_current_box}")
                else:
                    print(f"设备 {target} 不存在，可用设备: {list(_devices.keys())}")

        # 列出设备
        elif cmd_lower == "list":
            with _devices_lock:
                if not _devices:
                    print("[Server]暂无连接设备")
                else:
                    print(f"[Server]已连接 {len(_devices)} 个设备:")
                    for box_id in _devices:
                        dev = _devices[box_id]
                        status = dev.get("status", {})
                        led = "ON" if status.get("led") else "OFF"
                        mode = status.get("mode", "?")
                        marker = " <- 当前" if box_id == _current_box else ""
                        print(f"  {box_id}  LED={led}  Mode={mode}{marker}")

        # 退出
        elif cmd_lower == "exit":
            print("[Server]退出")
            break

        # 发送命令给当前设备
        else:
            with _devices_lock:
                cur = _current_box

            if cur is None:
                print("[Server]没有已连接的设备")
                continue

            if cmd_lower in ("on", "off", "auto", "manual", "status",
                              "light", "human", "sensor", "ip", "box_id",
                              "screen_on", "screen_off", "screen_invert",
                              "screen_normal", "help"):
                send_command(cur, {"cmd": cmd_lower})
            elif cmd_lower.startswith("contrast"):
                parts = user_cmd.split()
                val = 180
                if len(parts) >= 2:
                    try:
                        val = int(parts[1])
                    except:
                        pass
                send_command(cur, {"cmd": "contrast", "val": val})
            else:
                print("未知指令。支持: on/off/auto/manual/status | switch <设备名> | list | exit")


# ==================== 入口 ====================

def main():
    threading.Thread(target=accept_loop, daemon=True).start()
    cli_loop()


if __name__ == '__main__':
    main()
