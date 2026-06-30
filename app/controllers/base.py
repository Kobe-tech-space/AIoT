# Controller 公共基类

import tornado.web
from app.models.user import UserRepository


class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        username = self.get_secure_cookie("username")
        if not username:
            return None
        username = username.decode("utf-8")

        # 检查用户是否被禁用
        if UserRepository.is_user_disabled(username):
            self.clear_cookie("username")
            return None

        return username

    def is_admin(self):
        username = self.current_user
        if not username:
            return False
        row = UserRepository.get_user_by_username(username)
        return row and row["is_admin"] == 1

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def options(self):
        self.set_status(204)
        self.finish()

    def prepare(self):
        pass


class MobileBaseHandler(BaseHandler):
    """移动端 API 基类：跳过 XSRF 校验"""

    def check_xsrf_cookie(self):
        pass  # 移动端不校验 XSRF
