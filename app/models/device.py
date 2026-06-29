"""
设备相关 Model（Repository）
"""

import sqlite3
from app.models.db import get_connection


class DeviceRepository:

    # ==================== 创建设备 ====================

    @staticmethod
    def create_device(box_id, name, category, manage_url, sensors):
        try:
            with get_connection() as conn:
                conn.execute(
                    """INSERT INTO devices (box_id, name, category, manage_url, sensors)
                       VALUES (?, ?, ?, ?, ?)""",
                    (box_id, name, category, manage_url, sensors),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    # ==================== 查询设备 ====================

    @staticmethod
    def get_device_by_id(device_id):
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM devices WHERE id = ?", (device_id,)
            ).fetchone()

    @staticmethod
    def list_devices(page=1, page_size=6, keyword=""):
        offset = (page - 1) * page_size
        if keyword:
            kw = f"%{keyword}%"
            with get_connection() as conn:
                rows = conn.execute(
                    """SELECT * FROM devices
                       WHERE box_id LIKE ? OR name LIKE ? OR category LIKE ?
                       ORDER BY id DESC
                       LIMIT ? OFFSET ?""",
                    (kw, kw, kw, page_size, offset),
                ).fetchall()
                total = conn.execute(
                    """SELECT COUNT(*) as cnt FROM devices
                       WHERE box_id LIKE ? OR name LIKE ? OR category LIKE ?""",
                    (kw, kw, kw),
                ).fetchone()["cnt"]
        else:
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM devices ORDER BY id DESC LIMIT ? OFFSET ?",
                    (page_size, offset),
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) as cnt FROM devices").fetchone()["cnt"]
        return rows, total

    # ==================== 更新设备 ====================

    @staticmethod
    def update_device(device_id, box_id=None, name=None, category=None,
                      manage_url=None, sensors=None, status=None, esp32_ip=None):
        fields = []
        values = []
        if box_id is not None:
            fields.append("box_id = ?")
            values.append(box_id)
        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if category is not None:
            fields.append("category = ?")
            values.append(category)
        if manage_url is not None:
            fields.append("manage_url = ?")
            values.append(manage_url)
        if sensors is not None:
            fields.append("sensors = ?")
            values.append(sensors)
        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if esp32_ip is not None:
            fields.append("esp32_ip = ?")
            values.append(esp32_ip)

        if not fields:
            return True

        values.append(device_id)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE devices SET {', '.join(fields)} WHERE id = ?",
                values,
            )
        return True

    # ==================== 删除设备 ====================

    @staticmethod
    def delete_device(device_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        return True

    # ==================== 查询所有设备（不分页，用于下拉） ====================

    @staticmethod
    def all_devices():
        with get_connection() as conn:
            return conn.execute(
                "SELECT id, box_id, name FROM devices ORDER BY id DESC"
            ).fetchall()
