# CDUTAgentOS — 开发规范（AI 维护）

## 产品定位

CDUTAgentOS 是一套面向 AIoT 场景的设备管理与智能调度平台，提供从设备接入、数据采集、模型推理到指令下发的完整闭环。

---

## 技术架构

| 层级 | 选型 | 理由 |
|------|------|------|
| Web 服务 | Tornado 6.x | 单进程高并发，适合设备长连接场景 |
| 数据存储 | SQLite 3.x | 轻量嵌入，适合边缘部署 |
| 认证安全 | PBKDF2-SHA256 (100k iter) | 抗暴力破解，无明文存储 |
| 前端框架 | LayUI v2.13.7 | `dist/layui/` 完整组件包，含表格/表单/弹层/导航等全部模块 |
| 模板引擎 | Tornado Template | 内置，零额外依赖 |
| 通信协议 | JSON + \n (TCP) | 与 ESP32 设备直通，无需 MQTT 中间件 |

---

## 项目结构

```
CDUTAgentOS/
├── app.py                    # 应用入口 + 路由注册 + IOLoop
├── database/
│   └── app.db                # 生产数据（单文件，易备份迁移）
├── app/
│   ├── controllers/          # Handler 层
│   │   ├── base.py           #   基类：get_current_user() 登录态
│   │   ├── auth.py           #   认证：登录/注册/退出
│   │   └── home.py           #   首页：仪表盘
│   ├── models/               # 数据层
│   │   ├── db.py             #   连接池 + 建表迁移
│   │   └── user.py           #   用户仓储
│   ├── templates/            # 视图层
│   │   ├── base.html         #   全局布局
│   │   ├── index.html        #   首页
│   │   ├── login.html        #   登录
│   │   └── register.html     #   注册
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── dist/layui/               # LayUI v2.13.7 完整组件包
│   ├── layui.js               #   核心库
│   ├── css/layui.css          #   样式库
│   └── font/                  #   图标字体
└── docs/
    ├── codingPrompt.md       # 需求规格（产品维护）
    ├── basePrompt.md         # 技术规范（AI 维护）
    └── soul.md               # 产品愿景（AI 维护）
```

---

## 路由表

| 方法 | 路径 | Handler | 认证 |
|------|------|---------|------|
| GET | `/` | IndexHandler | 需要登录 |
| GET/POST | `/auth/login` | LoginHandler | 公开 |
| GET/POST | `/auth/register` | RegisterHandler | 公开 |
| POST | `/auth/logout` | LogoutHandler | 公开 |

---

## 数据库

### users

| 字段 | 类型 | 约束 |
|------|------|------|
| id | INTEGER | PK AUTOINCREMENT |
| username | TEXT | UNIQUE NOT NULL |
| password_hash | TEXT | NOT NULL |
| salt | TEXT | NOT NULL |
| created_at | TEXT | DEFAULT datetime('now') |

---

## 开发约定

### 控制器
- 一模块一文件，继承 `BaseHandler`
- 认证接口放在 `auth.py`，业务接口独立文件
- 表单 POST 必须携带 `xsrf_form_html()`

### 模型
- 静态方法仓储类，不实例化
- 统一通过 `get_connection()` 获取连接
- 密码操作走 `_hash_password()`，不直接处理原文

### 视图
- 所有页面继承 `base.html`
- 静态资源用 `{{ static_url() }}` 引用（如 `{{ static_url('css/style.css') }}`）
- LayUI 通过 `<script src="/dist/layui/layui.js">` 在 `base.html` 中全局引入，业务页面按需 `layui.use(['table','form'])`
- 错误信息统一用 `{% if error %}` 块展示

### 配置
- 应用级配置集中在 `app.py` 的 `settings` 字典
- `cookie_secret` 生产环境必须更换为随机字符串
- 端口默认 8888，被占则自动递增至 8907

---

## 新增模块步骤

1. `app/models/` 新建模型类
2. `app/controllers/` 新建 Handler
3. `app/templates/` 新建模板页面
4. `app.py` 的 `Application` 中注册路由
5. 需要新样式追加到 `style.css`，使用 LayUI 组件优先
