# 数字孪生 Controller
import json
import time
from app.controllers.base import BaseHandler
from app.controllers.server_manager import get_online_devices


class TwinPageHandler(BaseHandler):
    """数字孪生 3D 页面"""

    def get(self):
        self.render("twin.html", title="数字孪生")


class TwinStatusHandler(BaseHandler):
    """实时设备状态 API（供 3D 前端轮询）"""

    def get(self):
        devices = get_online_devices()
        data = []
        for bid, dev in devices.items():
            status = dev.get("status", {})
            data.append({
                "box_id": bid,
                "led": bool(status.get("led", 0)),
                "led_living": bool(status.get("led_living", 0)),
                "led_bed1": bool(status.get("led_bed1", 0)),
                "led_bed2": bool(status.get("led_bed2", 0)),
                "pir": bool(status.get("pir", 0)),
                "mode": status.get("mode", "manual"),
                "last_seen": int(time.time() - dev.get("last_seen", 0)),
            })
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({"code": 0, "data": data}, ensure_ascii=False))
