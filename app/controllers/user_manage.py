# 用户管理 Controller（管理员功能）

import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.user import UserRepository


def admin_required(method):
    """装饰器：要求管理员权限"""
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            self.redirect("/auth/login")
            return
        if not self.is_admin():
            self.set_status(403)
            self.finish("需要管理员权限")
            return
        return method(self, *args, **kwargs)
    return wrapper


class UserListHandler(BaseHandler):
    """GET: 用户列表页（管理员）"""

    @admin_required
    def get(self):
        self.render("user_list.html", title="用户管理")


class UserApiHandler(BaseHandler):
    """用户管理 API（JSON 接口）"""

    @admin_required
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        keyword = self.get_argument("keyword", "")

        rows, total = UserRepository.list_users(page, limit, keyword)
        data = []
        for r in rows:
            data.append({
                "id": r["id"],
                "username": r["username"],
                "nickname": r["nickname"],
                "phone": r["phone"],
                "status": r["status"],
                "is_admin": r["is_admin"],
                "created_at": r["created_at"],
            })

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({
            "code": 0,
            "msg": "",
            "count": total,
            "data": data,
        }, ensure_ascii=False))

    @admin_required
    def post(self):
        """新增用户"""
        username = (self.get_body_argument("username", "") or "").strip()
        password = self.get_body_argument("password", "")
        nickname = (self.get_body_argument("nickname", "") or "").strip()
        phone = (self.get_body_argument("phone", "") or "").strip()
        is_admin = int(self.get_body_argument("is_admin", "0") or "0")

        if not username or not password:
            self.write(json.dumps({"code": 1, "msg": "用户名和密码不能为空"}, ensure_ascii=False))
            return

        if not nickname:
            self.write(json.dumps({"code": 1, "msg": "昵称不能为空"}, ensure_ascii=False))
            return

        created = UserRepository.create_user(username, password, nickname, phone, is_admin)
        if not created:
            self.write(json.dumps({"code": 1, "msg": "用户名已存在"}, ensure_ascii=False))
            return

        self.write(json.dumps({"code": 0, "msg": "添加成功"}, ensure_ascii=False))

    @admin_required
    def put(self):
        """编辑用户"""
        user_id = int(self.get_body_argument("id"))
        nickname = (self.get_body_argument("nickname", "") or "").strip()
        phone = (self.get_body_argument("phone", "") or "").strip()
        password = self.get_body_argument("password", "")
        is_admin = self.get_body_argument("is_admin", None)
        if is_admin is not None:
            is_admin = int(is_admin)

        UserRepository.update_user(
            user_id,
            nickname=nickname if nickname else None,
            phone=phone if phone else None,
            password=password if password else None,
            is_admin=is_admin if is_admin in (0, 1) else None,
        )

        self.write(json.dumps({"code": 0, "msg": "修改成功"}, ensure_ascii=False))

    @admin_required
    def delete(self):
        """删除用户"""
        user_id = int(self.get_body_argument("id"))
        # 不允许删除自己
        row = UserRepository.get_user_by_id(user_id)
        if row and row["username"] == self.current_user:
            self.write(json.dumps({"code": 1, "msg": "不能删除自己的账号"}, ensure_ascii=False))
            return
        UserRepository.delete_user(user_id)
        self.write(json.dumps({"code": 0, "msg": "删除成功"}, ensure_ascii=False))


class UserToggleHandler(BaseHandler):
    """POST: 启用/禁用用户"""

    @admin_required
    def post(self):
        user_id = int(self.get_body_argument("id"))
        row = UserRepository.get_user_by_id(user_id)
        if row and row["username"] == self.current_user:
            self.write(json.dumps({"code": 1, "msg": "不能禁用自己的账号"}, ensure_ascii=False))
            return
        new_status = UserRepository.toggle_status(user_id)
        if new_status is None:
            self.write(json.dumps({"code": 1, "msg": "用户不存在"}, ensure_ascii=False))
            return
        msg = "已启用" if new_status == 1 else "已禁用"
        self.write(json.dumps({"code": 0, "msg": msg, "status": new_status}, ensure_ascii=False))
