# AIoT 服务器管理 Controller

import json
import socket
import threading
import time

from app.controllers.base import BaseHandler
from app.controllers.user_manage import admin_required
from app.models.operation_log import OperationLogRepository
from app.models.tcpserver import TcpServerRepository

# ==================== 服务器运行时注册表 ====================
_running_servers = {}   # { server_id: {"thread": Thread, "stop": Event} }
_runtime_lock = threading.Lock()

# 所有运行中服务器共享的设备注册表
_online_devices = {}
_devices_lock = threading.Lock()

# 每台服务器的实时日志（最近50条）
_server_logs = {}  # { server_id: [{"time":"HH:MM:SS", "text":"...", "cls":"sys/info/warn/ok"}, ...] }
_logs_lock = threading.Lock()


def _emit(server_id, text, cls="info"):
    t = time.strftime("%H:%M:%S")
    with _logs_lock:
        if server_id not in _server_logs:
            _server_logs[server_id] = []
        _server_logs[server_id].append({"time": t, "text": text, "cls": cls})
        if len(_server_logs[server_id]) > 50:
            _server_logs[server_id] = _server_logs[server_id][-50:]


def start_tcp_server(server_id, port):
    """后台启动一个 TCP 服务器实例"""
    stop_event = threading.Event()

    def _run():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1)  # 允许优雅退出
        try:
            sock.bind(('0.0.0.0', port))
            sock.listen(10)
        except Exception as e:
            print(f"[TCPServer:{server_id}] 启动失败: {e}")
            TcpServerRepository.set_status(server_id, 0)
            return

        print(f"[TCPServer:{server_id}] 已启动，监听端口 {port}")
        _emit(server_id, f"SYSTEM TCPServer 启动在端口 {port}", "sys")

        while not stop_event.is_set():
            try:
                conn, addr = sock.accept()
                threading.Thread(
                    target=_handle_device, args=(conn, addr, server_id),
                    daemon=True,
                ).start()
            except socket.timeout:
                continue
            except Exception:
                break

        sock.close()
        print(f"[TCPServer:{server_id}] 已停止")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    with _runtime_lock:
        _running_servers[server_id] = {
            "thread": thread,
            "stop": stop_event,
        }


def stop_tcp_server(server_id):
    """停止一个 TCP 服务器实例"""
    with _runtime_lock:
        info = _running_servers.pop(server_id, None)
    if info:
        info["stop"].set()
        TcpServerRepository.set_status(server_id, 0)


def _handle_device(conn, addr, server_id):
    """处理来自 ESP32 的数据（与 Server.py 兼容）"""
    import json as _json
    buf = b""
    box_id = None

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
                    msg = _json.loads(line.decode('utf-8'))
                except:
                    continue

                msg_type = msg.get("type")

                if msg_type == "register":
                    box_id = msg.get("box_id", f"{addr[0]}:{addr[1]}")
                    with _devices_lock:
                        _online_devices[box_id] = {
                            "conn": conn,
                            "addr": addr,
                            "status": {"led": 0, "light": 0, "pir": 0, "mode": "-"},
                            "last_seen": time.time(),
                            "server_id": server_id,
                        }
                    _update_device_status(box_id, 1, addr[0])
                    _emit(server_id, f"AI智能终端盒子上线 {box_id}  连接成功", "ok")
                    OperationLogRepository.add_log("设备上线", box_id, "系统", "连接", f"来自 {addr[0]}")
                    print(f"[TCPServer:{server_id}] {box_id} 上线")

                elif msg_type in ("status", "heartbeat") and box_id:
                    with _devices_lock:
                        if box_id in _online_devices:
                            _online_devices[box_id]["status"] = msg
                            _online_devices[box_id]["last_seen"] = time.time()
                            _online_devices[box_id]["server_id"] = server_id
                    led = "ON" if msg.get("led") else "OFF"
                    light = "Dark" if msg.get("light") else "Bright"
                    pir = "Body" if msg.get("pir") else "None"
                    mode = msg.get("mode", "-")
                    _emit(server_id, f"{box_id}  LED:{led}  光敏:{light}  人体:{pir}  模式:{mode}", "info")
                    OperationLogRepository.add_log("状态上报", box_id, "设备", "上报", f"LED:{led} 光敏:{light} 人体:{pir} 模式:{mode}")

                elif msg_type == "info" and box_id:
                    cmd = msg.get("cmd", "")
                    data = msg.get("data", {})
                    OperationLogRepository.add_log("指令响应", box_id, "设备", cmd, json.dumps(data, ensure_ascii=False))
                    if cmd == "light":
                        _emit(server_id, f"{box_id}  光敏: {data.get('text','?')} (值={data.get('value','?')})", "info")
                    elif cmd == "human":
                        _emit(server_id, f"{box_id}  人体: {data.get('text','?')} (值={data.get('value','?')})", "info")
                    elif cmd == "sensor":
                        light_t = "Dark" if data.get("light") else "Bright"
                        pir_t = "Body" if data.get("pir") else "None"
                        _emit(server_id, f"{box_id}  光敏:{light_t}  人体:{pir_t}", "info")
                    elif cmd == "ip":
                        _emit(server_id, f"{box_id}  设备IP:{data.get('device_ip','?')}  服务器:{data.get('server_ip','?')}:{data.get('server_port','?')}", "info")
                    elif cmd == "box_id":
                        _emit(server_id, f"{box_id}  BoxID: {data.get('box_id','?')}", "info")
                    elif cmd == "help":
                        cmds = ", ".join(data.get("commands", []))
                        _emit(server_id, f"{box_id}  可用指令: {cmds}", "info")
                    else:
                        _emit(server_id, f"{box_id}  {cmd}: {json.dumps(data, ensure_ascii=False)}", "info")

                elif msg_type == "ack" and box_id:
                    result = msg.get("result", "")
                    reason = msg.get("reason", "")
                    cmd = msg.get("cmd", "")
                    if result == "ok":
                        _emit(server_id, f"{box_id}  {cmd} -> OK", "ok")
                        OperationLogRepository.add_log("指令响应", box_id, "设备", cmd, "OK")
                    else:
                        _emit(server_id, f"{box_id}  {cmd} -> ERR: {reason}", "err")
                        OperationLogRepository.add_log("指令响应", box_id, "设备", cmd, f"ERR: {reason}")

        except Exception:
            break

    if box_id:
        device_addr = None
        with _devices_lock:
            if box_id in _online_devices:
                device_addr = _online_devices[box_id]["addr"][0]
                del _online_devices[box_id]
        _update_device_status(box_id, 0, device_addr)
    conn.close()


def _update_device_status(box_id, status, device_ip=None):
    """更新设备表中对应设备的在线状态"""
    try:
        from app.models.db import get_connection
        with get_connection() as conn:
            device = conn.execute(
                "SELECT id FROM devices WHERE box_id = ?", (box_id,)
            ).fetchone()
            if device:
                conn.execute(
                    "UPDATE devices SET status = ?, esp32_ip = ? WHERE box_id = ?",
                    (status, device_ip or "", box_id),
                )
    except:
        pass


def get_online_devices():
    with _devices_lock:
        return dict(_online_devices)


# ==================== Web Handler ====================

class ServerListHandler(BaseHandler):
    """服务器管理页面"""

    @admin_required
    def get(self):
        self.render("server_list.html", title="服务器管理")


class ServerApiHandler(BaseHandler):
    """服务器 API"""

    @admin_required
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 6))
        keyword = self.get_argument("keyword", "")

        rows, total = TcpServerRepository.list_servers(page, limit, keyword)
        online = get_online_devices()
        data = []
        for r in rows:
            running = r["id"] in _running_servers
            # 统计该服务器连接的设备
            devices = []
            events = []
            print(f"[API] server {r['id']} running={running}, online_devices={list(online.keys())}")
            for box_id, dev in online.items():
                print(f"[API] check: dev.server_id={dev.get('server_id')} vs r.id={r['id']} match={dev.get('server_id') == r['id']}")
                if dev.get("server_id") == r["id"]:
                    devices.append(box_id)
                    status = dev.get("status", {})
                    since = int(time.time() - dev.get("last_seen", 0))
                    events.append({
                        "box_id": box_id,
                        "led": status.get("led", 0),
                        "mode": status.get("mode", "-"),
                        "since": since,
                    })

            with _logs_lock:
                logs = _server_logs.get(r["id"], [])[-20:]  # 最近20条

            data.append({
                "id": r["id"], "name": r["name"], "port": r["port"],
                "status": 1 if running else 0,
                "running": running,
                "device_count": len(devices),
                "devices": devices,
                "events": events,
                "logs": logs,
                "created_at": r["created_at"],
            })

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({"code": 0, "count": total, "data": data}, ensure_ascii=False))

    @admin_required
    def post(self):
        name = (self.get_body_argument("name", "") or "").strip()
        port = int(self.get_body_argument("port", "0"))

        if not name or not port:
            self.write(json.dumps({"code": 1, "msg": "名称和端口不能为空"}, ensure_ascii=False))
            return

        if not TcpServerRepository.create_server(name, port):
            self.write(json.dumps({"code": 1, "msg": "端口已存在"}, ensure_ascii=False))
            return

        self.write(json.dumps({"code": 0, "msg": "添加成功"}, ensure_ascii=False))

    @admin_required
    def put(self):
        server_id = int(self.get_body_argument("id"))
        name = (self.get_body_argument("name", "") or "").strip()
        port_str = (self.get_body_argument("port", "") or "").strip()

        kwargs = {}
        if name:
            kwargs["name"] = name
        if port_str:
            kwargs["port"] = int(port_str)

        TcpServerRepository.update_server(server_id, **kwargs)
        self.write(json.dumps({"code": 0, "msg": "修改成功"}, ensure_ascii=False))

    @admin_required
    def delete(self):
        server_id = int(self.get_body_argument("id"))
        stop_tcp_server(server_id)
        TcpServerRepository.delete_server(server_id)
        self.write(json.dumps({"code": 0, "msg": "删除成功"}, ensure_ascii=False))


class ServerToggleHandler(BaseHandler):
    """启动/停止服务器"""

    @admin_required
    def post(self):
        server_id = int(self.get_body_argument("id"))
        action = (self.get_body_argument("action", "") or "").strip()

        server = TcpServerRepository.get_server_by_id(server_id)
        if not server:
            self.write(json.dumps({"code": 1, "msg": "服务器不存在"}, ensure_ascii=False))
            return

        if action == "start":
            if server_id in _running_servers:
                self.write(json.dumps({"code": 1, "msg": "已在运行中"}, ensure_ascii=False))
                return
            start_tcp_server(server_id, server["port"])
            TcpServerRepository.set_status(server_id, 1)
            self.write(json.dumps({"code": 0, "msg": "已启动"}, ensure_ascii=False))

        elif action == "stop":
            if server_id not in _running_servers:
                self.write(json.dumps({"code": 1, "msg": "未在运行"}, ensure_ascii=False))
                return
            stop_tcp_server(server_id)
            self.write(json.dumps({"code": 0, "msg": "已停止"}, ensure_ascii=False))

        else:
            self.write(json.dumps({"code": 1, "msg": "未知操作"}, ensure_ascii=False))


def send_device_command(server_id, box_id, cmd):
    """向指定设备的 TCP 连接发送 JSON 指令"""
    with _devices_lock:
        dev = _online_devices.get(box_id)
    if not dev:
        return False
    try:
        line = json.dumps({"cmd": cmd}) + "\n"
        dev["conn"].sendall(line.encode('utf-8'))
        _emit(server_id, f">>> send {box_id} {json.dumps({'cmd': cmd})}", "warn")
        OperationLogRepository.add_log("指令下发", box_id, "管理员", cmd, "")
        return True
    except Exception as e:
        _emit(server_id, f"> {cmd} 发送失败: {e}", "err")
        return False


class ServerCommandHandler(BaseHandler):
    """下发指令到设备"""

    @admin_required
    def post(self):
        server_id = int(self.get_body_argument("server_id"))
        box_id = (self.get_body_argument("box_id", "") or "").strip()
        cmd = (self.get_body_argument("cmd", "") or "").strip().lower()

        if not box_id or cmd not in (
            "on", "off", "auto", "manual", "status",
            "light", "human", "sensor", "ip", "box_id",
            "screen_on", "screen_off", "screen_invert", "screen_normal",
            "contrast", "help", "set_interval",
        ):
            self.write(json.dumps({"code": 1, "msg": "参数无效"}, ensure_ascii=False))
            return

        ok = send_device_command(server_id, box_id, cmd)
        if ok:
            self.write(json.dumps({"code": 0, "msg": f"指令 {cmd} 已发送"}, ensure_ascii=False))
        else:
            self.write(json.dumps({"code": 1, "msg": "设备不在线"}, ensure_ascii=False))


class DeviceStatusHandler(BaseHandler):
    """获取在线设备列表"""

    @admin_required
    def get(self):
        devices = get_online_devices()
        data = []
        for box_id, dev in devices.items():
            status = dev.get("status", {})
            data.append({
                "box_id": box_id,
                "addr": f"{dev['addr'][0]}:{dev['addr'][1]}",
                "led": status.get("led", 0),
                "light": status.get("light", 0),
                "pir": status.get("pir", 0),
                "mode": status.get("mode", "-"),
                "last_seen": int(time.time() - dev.get("last_seen", 0)),
            })
        self.write(json.dumps({"code": 0, "data": data}, ensure_ascii=False))
