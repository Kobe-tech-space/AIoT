# 认证相关 Controller（登录/注册/退出）

import tornado.web

from app.controllers.base import BaseHandler
from app.models.user import UserRepository


class LoginHandler(BaseHandler):

    def get(self):
        self.render("login.html", title="登录", error=None)

    def post(self):
        username = (self.get_body_argument("username", "") or "").strip()
        password = self.get_body_argument("password", "")

        if not username or not password:
            self.set_status(400)
            return self.render("login.html", title="登录", error="请输入用户名和密码")

        row = UserRepository.verify_user(username, password)
        if not row:
            self.set_status(401)
            return self.render("login.html", title="登录", error="用户名或密码错误")

        # 检查账号是否被禁用
        if row["status"] == 0:
            self.set_status(403)
            return self.render("login.html", title="登录", error="该账号已被禁用，请联系管理员")

        self.set_secure_cookie("username", username)
        self.redirect("/")


class RegisterHandler(BaseHandler):

    def get(self):
        self.render("register.html", title="注册", error=None)

    def post(self):
        username = (self.get_body_argument("username", "") or "").strip()
        password = self.get_body_argument("password", "")
        password2 = self.get_body_argument("password2", "")
        nickname = (self.get_body_argument("nickname", "") or "").strip()
        phone = (self.get_body_argument("phone", "") or "").strip()

        if not username or not password:
            self.set_status(400)
            return self.render("register.html", title="注册", error="请输入用户名和密码")

        if password != password2:
            self.set_status(400)
            return self.render("register.html", title="注册", error="两次密码不一致")

        if not nickname:
            self.set_status(400)
            return self.render("register.html", title="注册", error="请输入昵称")

        created = UserRepository.create_user(username, password, nickname, phone)
        if not created:
            self.set_status(409)
            return self.render("register.html", title="注册", error="用户名已存在")

        self.redirect("/auth/login")


class LogoutHandler(BaseHandler):

    def post(self):
        self.clear_cookie("username")
        self.redirect("/auth/login")
