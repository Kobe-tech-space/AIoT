"""
AI 模型引擎 Model（Repository）
"""

from app.models.db import get_connection


class AiModelRepository:

    @staticmethod
    def create_model(name, api_key, api_url, model_name, temperature=0.7, max_tokens=2048):
        with get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO ai_models (name, api_key, api_url, model_name, temperature, max_tokens)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, api_key, api_url, model_name, temperature, max_tokens),
            )
            return cursor.lastrowid

    @staticmethod
    def get_model_by_name(model_name):
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM ai_models WHERE model_name = ? LIMIT 1", (model_name,)
            ).fetchone()

    @staticmethod
    def get_model_by_id(model_id):
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM ai_models WHERE id = ?", (model_id,)
            ).fetchone()

    @staticmethod
    def get_default_model():
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM ai_models WHERE is_default = 1 LIMIT 1"
            ).fetchone()

    @staticmethod
    def list_models(page=1, page_size=6, keyword=""):
        offset = (page - 1) * page_size
        if keyword:
            kw = f"%{keyword}%"
            with get_connection() as conn:
                rows = conn.execute(
                    """SELECT * FROM ai_models WHERE name LIKE ? OR model_name LIKE ?
                       ORDER BY id DESC LIMIT ? OFFSET ?""",
                    (kw, kw, page_size, offset),
                ).fetchall()
                total = conn.execute(
                    "SELECT COUNT(*) as cnt FROM ai_models WHERE name LIKE ? OR model_name LIKE ?",
                    (kw, kw),
                ).fetchone()["cnt"]
        else:
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM ai_models ORDER BY id DESC LIMIT ? OFFSET ?",
                    (page_size, offset),
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) as cnt FROM ai_models").fetchone()["cnt"]
        return rows, total

    @staticmethod
    def update_model(model_id, **kwargs):
        fields = []
        values = []
        for key, val in kwargs.items():
            if val is not None:
                fields.append(f"{key} = ?")
                values.append(val)
        if not fields:
            return True
        values.append(model_id)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE ai_models SET {', '.join(fields)} WHERE id = ?",
                values,
            )
        return True

    @staticmethod
    def delete_model(model_id):
        with get_connection() as conn:
            conn.execute("DELETE FROM ai_models WHERE id = ?", (model_id,))
        return True

    @staticmethod
    def set_default(model_id):
        with get_connection() as conn:
            conn.execute("UPDATE ai_models SET is_default = 0")
            conn.execute("UPDATE ai_models SET is_default = 1 WHERE id = ?", (model_id,))
        return True

    @staticmethod
    def seed_builtin():
        if not AiModelRepository.get_default_model():
            AiModelRepository.create_model(
                name="qwen3.5-flash",
                api_key="sk-aigc-74417635957c145bcc72f4687569e4e07b2c0b43",
                api_url="https://aigc-api.aitoolcore.com/api/v1",
                model_name="qwen3.5-flash",
                temperature=0.7,
                max_tokens=2048,
            )
            with get_connection() as conn:
                conn.execute("UPDATE ai_models SET is_default = 1 WHERE model_name = 'qwen3.5-flash'")

        # TTS 模型（语音合成）
        if not AiModelRepository.get_model_by_name("cosyvoice-v3-flash"):
            AiModelRepository.create_model(
                name="cosyvoice-v3-flash (TTS)",
                api_key="sk-aigc-74417635957c145bcc72f4687569e4e07b2c0b43",
                api_url="https://aigc-api.aitoolcore.com/api/v1",
                model_name="cosyvoice-v3-flash",
                temperature=1.0,
                max_tokens=4096,
            )
