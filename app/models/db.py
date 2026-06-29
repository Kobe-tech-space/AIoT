"""
SQLite 数据库访问层（Model 的基础设施部分）

教学点：
- 使用 Python 内置 sqlite3 连接 SQLite（零依赖）
- 统一管理 DB 文件路径、连接创建、row_factory
- init_db() 在启动时建表，保证 demo "开箱即用"
"""

import os
import sqlite3


def _project_root():
    # 获取项目根目录（.../cnAgentOS）
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


# 数据库文件路径：放在项目根目录/database/app.db
DB_PATH = os.path.join(_project_root(), "database", "app.db")


def get_connection():
    """
    获取一个 SQLite 连接。

    注意：sqlite3.connect 会在文件不存在时自动创建数据库文件。
    这里额外确保 database 目录存在，避免路径不存在导致创建失败。
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # 使用 sqlite3.Row 后，查询结果可以通过 row["column"] 方式访问
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn, table, column):
    result = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in result)


def init_db():
    """
    初始化数据库结构（建表）。

    CREATE TABLE IF NOT EXISTS 可重复执行，适合放在应用启动时调用。
    """
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )

        # 业务扩展字段：兼容旧库逐列补齐
        if not _column_exists(conn, "users", "nickname"):
            conn.execute("ALTER TABLE users ADD COLUMN nickname TEXT NOT NULL DEFAULT ''")
        if not _column_exists(conn, "users", "phone"):
            conn.execute("ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT ''")
        if not _column_exists(conn, "users", "status"):
            conn.execute("ALTER TABLE users ADD COLUMN status INTEGER NOT NULL DEFAULT 1")
        if not _column_exists(conn, "users", "is_admin"):
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")

        # 设备表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                esp32_ip TEXT NOT NULL DEFAULT '',
                manage_url TEXT NOT NULL DEFAULT '',
                sensors TEXT NOT NULL DEFAULT '[]',
                status INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )

        # 模型引擎表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                api_key TEXT NOT NULL DEFAULT '',
                api_url TEXT NOT NULL DEFAULT '',
                model_name TEXT NOT NULL DEFAULT '',
                temperature REAL NOT NULL DEFAULT 0.7,
                max_tokens INTEGER NOT NULL DEFAULT 2048,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )

        # 接口管理表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS external_apis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                api_type TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                api_key TEXT NOT NULL DEFAULT '',
                params TEXT NOT NULL DEFAULT '{}',
                status INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )

        # 操作日志表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT NOT NULL DEFAULT '',
                box_id TEXT NOT NULL DEFAULT '',
                operator TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL DEFAULT '',
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )

        # AIoT 服务器管理表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tcpservers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                port INTEGER NOT NULL UNIQUE,
                status INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
