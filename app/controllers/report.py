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


class StatsApiHandler(BaseHandler):
    """统计数据 API"""

    @admin_required
    def get(self):
        stats = OperationLogRepository.stats()
        self.write(json.dumps({"code": 0, "data": stats}, ensure_ascii=False))
