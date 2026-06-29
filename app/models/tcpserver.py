"""
AIoT 服务器管理 Model（Repository）
"""

import sqlite3
from app.models.db import get_connection


class TcpServerRepository:

    @staticmethod
    def create_server(name, port):
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO tcpservers (name, port) VALUES (?, ?)",
                    (name, port),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def get_server_by_id(server_id):
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM tcpservers WHERE id = ?", (server_id,)
            ).fetchone()

    @staticmethod
    def list_servers(page=1, page_size=6, keyword=""):
        offset = (page - 1) * page_size
        if keyword:
            kw = f"%{keyword}%"
            with get_connection() as conn:
                rows = conn.execute(
                    """SELECT * FROM tcpservers WHERE name LIKE ?
                       ORDER BY id DESC LIMIT ? OFFSET ?""",
                    (kw, page_size, offset),
                ).fetchall()
                total = conn.execute(
                    "SELECT COUNT(*) as cnt FROM tcpservers WHERE name LIKE ?",
                    (kw,),
                ).fetchone()["cnt"]
        else:
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM tcpservers ORDER BY id DESC LIMIT ? OFFSET ?",
                    (page_size, offset),
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) as cnt FROM tcpservers").fetchone()["cnt"]
        return rows, total

    @staticmethod
    def update_server(server_id, name=None, port=None):
        fields = []
        values = []
        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if port is not None:
            fields.append("port = ?")
            values.append(port)
        if not fields:
            return True
        values.append(server_id)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE tcpservers SET {', '.join(fields)} WHERE id = ?",
                values,
            )
        return True

    @staticmethod
    def set_status(server_id, status):
        with get_connection() as conn:
            conn.execute(
                "UPDATE tcpservers SET status = ? WHERE id = ?",
                (status, server_id),
            )

    @staticmethod
    def delete_server(server_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM tcpservers WHERE id = ?", (server_id,))
        return True

    @staticmethod
    def all_servers():
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM tcpservers ORDER BY id DESC"
            ).fetchall()
