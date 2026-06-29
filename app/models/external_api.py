"""
第三方接口管理 Model（Repository）
"""

from app.models.db import get_connection


class ExternalApiRepository:

    @staticmethod
    def create_api(name, api_type, url, api_key, params="{}"):
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO external_apis (name, api_type, url, api_key, params)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, api_type, url, api_key, params),
            )

    @staticmethod
    def get_api_by_id(api_id):
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM external_apis WHERE id = ?", (api_id,)
            ).fetchone()

    @staticmethod
    def list_apis(page=1, page_size=20, keyword=""):
        offset = (page - 1) * page_size
        if keyword:
            kw = f"%{keyword}%"
            with get_connection() as conn:
                rows = conn.execute(
                    """SELECT * FROM external_apis
                       WHERE name LIKE ? OR api_type LIKE ?
                       ORDER BY id DESC LIMIT ? OFFSET ?""",
                    (kw, kw, page_size, offset),
                ).fetchall()
                total = conn.execute(
                    "SELECT COUNT(*) as cnt FROM external_apis WHERE name LIKE ? OR api_type LIKE ?",
                    (kw, kw),
                ).fetchone()["cnt"]
        else:
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM external_apis ORDER BY id DESC LIMIT ? OFFSET ?",
                    (page_size, offset),
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) as cnt FROM external_apis").fetchone()["cnt"]
        return rows, total

    @staticmethod
    def update_api(api_id, **kwargs):
        fields = []
        values = []
        for key, val in kwargs.items():
            if val is not None:
                fields.append(f"{key} = ?")
                values.append(val)
        if not fields:
            return True
        values.append(api_id)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE external_apis SET {', '.join(fields)} WHERE id = ?",
                values,
            )
        return True

    @staticmethod
    def delete_api(api_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM external_apis WHERE id = ?", (api_id,))
        return True
