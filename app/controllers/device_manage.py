# 设备管理 Controller

import json
from app.controllers.base import BaseHandler
from app.controllers.user_manage import admin_required
from app.models.device import DeviceRepository


class DeviceListHandler(BaseHandler):
    """设备管理页面"""

    @admin_required
    def get(self):
        self.render("device_list.html", title="设备管理")


class DeviceApiHandler(BaseHandler):
    """设备管理 API"""

    @admin_required
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 6))
        keyword = self.get_argument("keyword", "")

        rows, total = DeviceRepository.list_devices(page, limit, keyword)
        data = []
        for r in rows:
            data.append({
                "id": r["id"],
                "box_id": r["box_id"],
                "name": r["name"],
                "category": r["category"],
                "esp32_ip": r["esp32_ip"],
                "manage_url": r["manage_url"],
                "sensors": r["sensors"],
                "status": r["status"],
                "created_at": r["created_at"],
            })

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({
            "code": 0, "msg": "", "count": total, "data": data,
        }, ensure_ascii=False))

    @admin_required
    def post(self):
        box_id = (self.get_body_argument("box_id", "") or "").strip()
        name = (self.get_body_argument("name", "") or "").strip()
        category = (self.get_body_argument("category", "") or "").strip()
        manage_url = (self.get_body_argument("manage_url", "") or "").strip()
        sensors = (self.get_body_argument("sensors", "[]") or "[]").strip()

        if not box_id or not name:
            self.write(json.dumps({"code": 1, "msg": "设备编号和名称不能为空"}, ensure_ascii=False))
            return

        created = DeviceRepository.create_device(box_id, name, category, manage_url, sensors)
        if not created:
            self.write(json.dumps({"code": 1, "msg": "设备编号已存在"}, ensure_ascii=False))
            return

        self.write(json.dumps({"code": 0, "msg": "添加成功"}, ensure_ascii=False))

    @admin_required
    def put(self):
        device_id = int(self.get_body_argument("id"))
        box_id = (self.get_body_argument("box_id", "") or "").strip()
        name = (self.get_body_argument("name", "") or "").strip()
        category = (self.get_body_argument("category", "") or "").strip()
        manage_url = (self.get_body_argument("manage_url", "") or "").strip()
        sensors = (self.get_body_argument("sensors", "[]") or "[]").strip()

        DeviceRepository.update_device(
            device_id,
            box_id=box_id if box_id else None,
            name=name if name else None,
            category=category if category else None,
            manage_url=manage_url if manage_url else None,
            sensors=sensors if sensors else None,
        )

        self.write(json.dumps({"code": 0, "msg": "修改成功"}, ensure_ascii=False))

    @admin_required
    def delete(self):
        device_id = int(self.get_body_argument("id"))
        DeviceRepository.delete_device(device_id)
        self.write(json.dumps({"code": 0, "msg": "删除成功"}, ensure_ascii=False))


class DeviceSensorHandler(BaseHandler):
    """预设传感器模板"""

    @admin_required
    def get(self):
        presets = [
            {"name": "光敏传感器", "pin": 34},
            {"name": "LED", "pin": 15},
            {"name": "人体红外", "pin": 17},
            {"name": "OLED", "pin": "I2C(21,22)"},
            {"name": "DHT22", "pin": 4},
        ]
        self.write(json.dumps({"code": 0, "data": presets}, ensure_ascii=False))
