# 用户相关 Model（Repository）

import hashlib
import secrets
import sqlite3

from app.models.db import get_connection


def _hash_password(password, salt):
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return dk.hex()


class UserRepository:

    # ==================== 创建用户 ====================

    @staticmethod
    def create_user(username, password, nickname="", phone="", is_admin=0):
        salt = secrets.token_bytes(16)
        password_hash = _hash_password(password, salt)

        try:
            with get_connection() as conn:
                conn.execute(
                    """INSERT INTO users (username, password_hash, salt, nickname, phone, is_admin)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (username, password_hash, salt.hex(), nickname, phone, is_admin),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    # ==================== 查询用户 ====================

    @staticmethod
    def get_user_by_username(username):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        return row

    @staticmethod
    def get_user_by_id(user_id):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return row

    @staticmethod
    def verify_user(username, password):
        row = UserRepository.get_user_by_username(username)
        if not row:
            return None
        salt = bytes.fromhex(row["salt"])
        if _hash_password(password, salt) != row["password_hash"]:
            return None
        return row

    # ==================== 用户列表（分页 + 搜索） ====================

    @staticmethod
    def list_users(page=1, page_size=20, keyword=""):
        offset = (page - 1) * page_size
        if keyword:
            kw = f"%{keyword}%"
            with get_connection() as conn:
                rows = conn.execute(
                    """SELECT id, username, nickname, phone, status, is_admin, created_at
                       FROM users
                       WHERE username LIKE ? OR nickname LIKE ? OR phone LIKE ?
                       ORDER BY id DESC
                       LIMIT ? OFFSET ?""",
                    (kw, kw, kw, page_size, offset),
                ).fetchall()
                total = conn.execute(
                    """SELECT COUNT(*) as cnt FROM users
                       WHERE username LIKE ? OR nickname LIKE ? OR phone LIKE ?""",
                    (kw, kw, kw),
                ).fetchone()["cnt"]
        else:
            with get_connection() as conn:
                rows = conn.execute(
                    """SELECT id, username, nickname, phone, status, is_admin, created_at
                       FROM users
                       ORDER BY id DESC
                       LIMIT ? OFFSET ?""",
                    (page_size, offset),
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
        return rows, total

    # ==================== 更新用户 ====================

    @staticmethod
    def update_user(user_id, nickname=None, phone=None, password=None, is_admin=None):
        fields = []
        values = []
        if nickname is not None:
            fields.append("nickname = ?")
            values.append(nickname)
        if phone is not None:
            fields.append("phone = ?")
            values.append(phone)
        if is_admin is not None:
            fields.append("is_admin = ?")
            values.append(is_admin)
        if password is not None:
            salt = secrets.token_bytes(16)
            password_hash = _hash_password(password, salt)
            fields.append("password_hash = ?")
            values.append(password_hash)
            fields.append("salt = ?")
            values.append(salt.hex())

        if not fields:
            return True

        values.append(user_id)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE id = ?",
                values,
            )
        return True

    # ==================== 删除用户 ====================

    @staticmethod
    def delete_user(user_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return True

    # ==================== 启用/禁用 ====================

    @staticmethod
    def toggle_status(user_id):
        with get_connection() as conn:
            row = conn.execute("SELECT status FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                return None
            new_status = 0 if row["status"] else 1
            conn.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
            return new_status

    # ==================== 检查用户是否被禁用 ====================

    @staticmethod
    def is_user_disabled(username):
        row = UserRepository.get_user_by_username(username)
        if not row:
            return True
        return row["status"] == 0
