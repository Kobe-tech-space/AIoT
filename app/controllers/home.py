"""
首页相关 Controller
"""

import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.db import get_connection
from app.controllers.server_manager import get_online_devices, _running_servers


class IndexHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        self.render("index.html", title="首页", username=self.current_user)


class DashboardApiHandler(BaseHandler):
    """首页仪表盘数据"""

    @tornado.web.authenticated
    def get(self):
        with get_connection() as conn:
            user_count = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
            device_count = conn.execute("SELECT COUNT(*) as cnt FROM devices").fetchone()["cnt"]
            model_count = conn.execute("SELECT COUNT(*) as cnt FROM ai_models").fetchone()["cnt"]
            api_count = conn.execute("SELECT COUNT(*) as cnt FROM external_apis").fetchone()["cnt"]
            server_count = conn.execute("SELECT COUNT(*) as cnt FROM tcpservers").fetchone()["cnt"]

        online = get_online_devices()
        online_count = len(online)
        running_servers = len(_running_servers)

        self.write(json.dumps({
            "user_count": user_count,
            "device_count": device_count,
            "online_count": online_count,
            "model_count": model_count,
            "api_count": api_count,
            "server_count": server_count,
            "running_servers": running_servers,
        }, ensure_ascii=False))
