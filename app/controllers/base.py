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

    def prepare(self):
        # 所有页面都可以获取 is_admin 变量
        pass
