# 数据报表 Controller

import json
from app.controllers.base import BaseHandler
from app.controllers.user_manage import admin_required
from app.models.operation_log import OperationLogRepository


class ReportPageHandler(BaseHandler):
    """数据报表页面"""

    @admin_required
    def get(self):
        self.render("report.html", title="数据报表")


class ReportApiHandler(BaseHandler):
    """报表 API"""

    @admin_required
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        log_type = self.get_argument("log_type", "")
        box_id = self.get_argument("box_id", "")
        keyword = self.get_argument("keyword", "")

        rows, total = OperationLogRepository.list_logs(page, limit, log_type, box_id, keyword)
        data = []
        for r in rows:
            data.append({
                "id": r["id"], "log_type": r["log_type"], "box_id": r["box_id"],
                "operator": r["operator"], "action": r["action"],
                "detail": r["detail"], "created_at": r["created_at"],
            })

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({"code": 0, "count": total, "data": data}, ensure_ascii=False))

    @admin_required
    def delete(self):
        """删除日志：单个 /api/reports?id=1  批量 /api/reports?ids=1,2,3"""
        log_id = self.get_argument("id", "")
        ids_str = self.get_argument("ids", "")

        if log_id:
            OperationLogRepository.delete_log(int(log_id))
            self.write(json.dumps({"code": 0, "msg": "删除成功"}, ensure_ascii=False))
        elif ids_str:
            ids = [int(x.strip()) for x in ids_str.split(",") if x.strip()]
            if ids:
                OperationLogRepository.delete_logs_batch(ids)
            self.write(json.dumps({"code": 0, "msg": f"已删除 {len(ids)} 条"}, ensure_ascii=False))
        else:
            self.write(json.dumps({"code": 1, "msg": "缺少 id 或 ids 参数"}, ensure_ascii=False))


class StatsApiHandler(BaseHandler):
    """统计数据 API"""

    @admin_required
    def get(self):
        stats = OperationLogRepository.stats()
        self.write(json.dumps({"code": 0, "data": stats}, ensure_ascii=False))
