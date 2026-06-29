"""
操作日志 Model（Repository）
"""

from app.models.db import get_connection


class OperationLogRepository:

    @staticmethod
    def add_log(log_type, box_id, operator, action, detail=""):
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO operation_logs (log_type, box_id, operator, action, detail)
                   VALUES (?, ?, ?, ?, ?)""",
                (log_type, box_id, operator, action, detail),
            )

    @staticmethod
    def list_logs(page=1, page_size=20, log_type="", box_id="", keyword=""):
        offset = (page - 1) * page_size
        conditions = []
        params = []

        if log_type:
            conditions.append("log_type = ?")
            params.append(log_type)
        if box_id:
            conditions.append("box_id = ?")
            params.append(box_id)
        if keyword:
            kw = f"%{keyword}%"
            conditions.append("(action LIKE ? OR detail LIKE ? OR operator LIKE ?)")
            params.extend([kw, kw, kw])

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM operation_logs {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [page_size, offset],
            ).fetchall()
            total = conn.execute(
                f"SELECT COUNT(*) as cnt FROM operation_logs {where}",
                params,
            ).fetchone()["cnt"]
        return rows, total

    @staticmethod
    def stats(hours=2):
        """返回统计数据：最近N小时各类型操作数量、设备活跃度、按分钟趋势"""
        with get_connection() as conn:
            type_stats = conn.execute(
                """SELECT log_type, COUNT(*) as cnt FROM operation_logs
                   WHERE created_at >= datetime('now', ?)
                   GROUP BY log_type ORDER BY cnt DESC""",
                (f"-{hours} hours",),
            ).fetchall()
            device_stats = conn.execute(
                """SELECT box_id, COUNT(*) as cnt FROM operation_logs
                   WHERE box_id != '' AND created_at >= datetime('now', ?)
                   GROUP BY box_id ORDER BY cnt DESC LIMIT 10""",
                (f"-{hours} hours",),
            ).fetchall()
            minute_stats = conn.execute(
                """SELECT strftime('%H:%M', created_at) as minute, COUNT(*) as cnt
                   FROM operation_logs
                   WHERE created_at >= datetime('now', ?)
                   GROUP BY minute ORDER BY minute""",
                (f"-{hours} hours",),
            ).fetchall()
        return {
            "type_stats": [{"name": r["log_type"], "value": r["cnt"]} for r in type_stats],
            "device_stats": [{"name": r["box_id"], "value": r["cnt"]} for r in device_stats],
            "minute_stats": [{"minute": r["minute"], "cnt": r["cnt"]} for r in minute_stats],
        }
