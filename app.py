"""
教学用 Tornado B/S Demo（MVC 三层架构 + SQLite）

整体结构：
- Controller：app/controllers/*.py（Tornado 的 RequestHandler）
- Model：app/models/*.py（SQLite 访问 + 业务方法）
- View：app/templates/*.html（Tornado 模板）

本文件是程序入口：
- 组装路由（URL -> Handler）
- 配置模板目录、静态文件目录、Cookie/XSRF 等
- 启动 HTTP 服务与 IOLoop
"""

import os

try:
    import tornado.ioloop
    import tornado.web
except ModuleNotFoundError as exc:
    raise SystemExit(
        "缺少依赖：tornado。\n"
        "  .\\venv\\Scripts\\Activate.ps1\n"
        "  python -m pip install tornado\n"
    ) from exc

from app.controllers.auth import LoginHandler, LogoutHandler, RegisterHandler
from app.controllers.home import IndexHandler, DashboardApiHandler
from app.controllers.report import ReportPageHandler, ReportApiHandler, StatsApiHandler
from app.controllers.ai_engine import (
    ModelListHandler, ModelApiHandler, ModelDefaultHandler, ModelChatHandler,
    ModelChatStreamHandler,
    ApiListHandler, ExternalApiHandler, ApiTestHandler,
)
from app.controllers.device_manage import DeviceListHandler, DeviceApiHandler, DeviceSensorHandler
from app.controllers.server_manager import (
    ServerListHandler, ServerApiHandler, ServerToggleHandler,
    ServerCommandHandler, DeviceStatusHandler,
)
from app.controllers.user_manage import UserListHandler, UserApiHandler, UserToggleHandler
from app.models.db import init_db
from app.models.ai_model import AiModelRepository
from app.models.user import UserRepository


def seed_admin():
    """预置默认账号"""
    if not UserRepository.get_user_by_username("admin"):
        UserRepository.create_user(
            username="admin", password="admin888",
            nickname="管理员", phone="", is_admin=1,
        )
        print("[Seed] 已创建管理员账号: admin / admin888")
    if not UserRepository.get_user_by_username("rexyang"):
        UserRepository.create_user(
            username="rexyang", password="123456",
            nickname="Rex", phone="", is_admin=0,
        )
        print("[Seed] 已创建用户账号: rexyang / 123456")


def make_app():
    """
    创建并返回 Tornado Application。

    Application 相当于"Web 应用容器"，负责：
    - 路由匹配
    - 中间件/配置（settings）
    - 统一的模板/静态目录
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    settings = dict(
        # View（视图层）：模板文件所在目录
        template_path=os.path.join(base_dir, "app", "templates"),
        # View（视图层）：静态资源（CSS/JS/图片）所在目录，对应 URL 前缀默认是 /static/
        static_path=os.path.join(base_dir, "app", "static"),
        # secure cookie 的签名密钥：用于防篡改 Cookie（set_secure_cookie/get_secure_cookie）
        cookie_secret="demo-cookie-secret-change-me",
        # 访问受保护页面（@authenticated）且未登录时，会跳转到此 URL
        login_url="/auth/login",
        # 开启 XSRF 防护：所有 form 的 POST 都需要带上 xsrf token
        xsrf_cookies=True,
        # 教学场景下开启 debug：自动重载、详细错误页（生产环境请关闭）
        debug=True,
        autoreload=True,
    )

    return tornado.web.Application(
        [
            # 首页：需要登录后访问
            (r"/", IndexHandler),
            (r"/api/dashboard", DashboardApiHandler),
            # 登录/注册/退出：完整的账号流程示例
            (r"/auth/login", LoginHandler),
            (r"/auth/register", RegisterHandler),
            (r"/auth/logout", LogoutHandler),
            # 用户管理
            (r"/users", UserListHandler),
            (r"/api/users", UserApiHandler),
            (r"/api/users/toggle", UserToggleHandler),
            # 设备管理
            (r"/devices", DeviceListHandler),
            (r"/api/devices", DeviceApiHandler),
            (r"/api/sensors", DeviceSensorHandler),
            # 模型引擎
            (r"/models", ModelListHandler),
            (r"/api/models", ModelApiHandler),
            (r"/api/models/default", ModelDefaultHandler),
            (r"/api/models/chat", ModelChatHandler),
            (r"/api/models/chat/stream", ModelChatStreamHandler),
            # 接口管理
            (r"/apis", ApiListHandler),
            (r"/api/external", ExternalApiHandler),
            (r"/api/external/test", ApiTestHandler),
            # 服务器管理
            (r"/servers", ServerListHandler),
            (r"/api/servers", ServerApiHandler),
            (r"/api/servers/toggle", ServerToggleHandler),
            (r"/api/servers/command", ServerCommandHandler),
            (r"/api/devices/online", DeviceStatusHandler),
            # 数据报表
            (r"/reports", ReportPageHandler),
            (r"/api/reports", ReportApiHandler),
            (r"/api/stats", StatsApiHandler),
        ],
        **settings,
    )


if __name__ == "__main__":
    # 启动前初始化数据库（建表）
    init_db()
    seed_admin()
    AiModelRepository.seed_builtin()
    app = make_app()
    # 监听端口：默认 8888；如被占用则自动尝试后续端口（便于教学时多开实例）
    base_port = int(os.environ.get("PORT", "8888"))
    for port in range(base_port, base_port + 20):
        try:
            app.listen(port)
            print(f"Server started: http://localhost:{port}/", flush=True)
            break
        except OSError as exc:
            if getattr(exc, "winerror", None) == 10048:
                continue
            raise
    else:
        raise SystemExit(f"启动失败：端口 {base_port}~{base_port + 19} 均被占用")
    # 启动事件循环（Tornado 基于 IOLoop 驱动）
    tornado.ioloop.IOLoop.current().start()
