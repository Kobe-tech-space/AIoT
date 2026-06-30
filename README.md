# CDUTAgentOS — AIoT 无线传感网智能体系统

## 项目简介

基于 Tornado MVC + SQLite + LayUI + uni-app x + Three.js 的 AIoT 设备管理平台。实现 ESP32 终端接入、TCP 通信、三灯独立控制、数字孪生 3D 可视化、AI 智能对话、移动端 APP、ECharts 数据报表的完整闭环。

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 后端 | Python 3.11 + Tornado |
| 数据库 | SQLite 3 |
| 前端框架 | LayUI v2.13.7 |
| 3D 渲染 | Three.js 0.160 |
| 移动端 | uni-app x (Vue 3 + uts) |
| AI 模型 | qwen3.5-flash (OpenAI 兼容 API) |
| TTS 语音 | qwen3-tts-flash / 浏览器 SpeechSynthesis |
| 图表 | ECharts 5.5 |
| 设备通信 | TCP + JSON 协议 (\n 分隔) |

## 快速启动

### 1. 启动后端

```powershell
cd project\CDUTAgentOS
.\venv\Scripts\Activate.ps1
python app.py
```

浏览器打开 `http://localhost:8888`

### 2. 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin888 | 管理员 |

### 3. TCP 服务器

左侧菜单 → 服务器管理 → 新增（名称 + 端口）→ 保存 → 启用

### 4. ESP32 烧录

将 `project/` 下 6 个文件烧录到 ESP32：

| 文件 | 说明 |
|------|------|
| `boot.py` | WiFi 连接 |
| `config.py` | 引脚/网络配置 |
| `main.py` | 主程序（三灯 + 传感器 + OLED） |
| `protocol.py` | JSON 协议 |
| `tcp_client.py` | TCP 客户端 |
| `ssd1306.py` | OLED 驱动 |

### 5. 移动端

HBuilderX 打开 `uniapp/CDUTAPP` → 运行到 Android App 基座

## 项目结构

```
CDUTAgentOS/
├── app.py                    # 入口：路由 + 配置 + 启动
├── app/
│   ├── controllers/          # Handler 层
│   │   ├── auth.py           #   登录/注册/退出
│   │   ├── home.py           #   首页仪表盘
│   │   ├── user_manage.py    #   用户管理
│   │   ├── device_manage.py  #   AIoT 设备管理
│   │   ├── server_manager.py #   TCP 服务器管理
│   │   ├── ai_engine.py      #   模型引擎 + TTS + 天气
│   │   ├── twin.py           #   数字孪生
│   │   └── report.py         #   数据报表
│   ├── models/               # 数据层
│   ├── templates/            # 视图层（含 twin.html 3D 场景）
│   └── static/               # 静态资源（LayUI）
├── database/                 # SQLite 数据库文件
├── docs/                     # 项目文档
├── skills/                   # AI 提示词
└── uniapp/CDUTAPP/           # 移动端项目
```

## ESP32 指令表

| 类别 | 指令 |
|------|------|
| 全控 | `on`, `off` |
| 客厅灯 | `living_on`, `living_off` |
| 卧室1灯 | `bed1_on`, `bed1_off` |
| 卧室2灯 | `bed2_on`, `bed2_off` |
| 模式 | `auto`, `manual` |
| 查询 | `status`, `light`, `human`, `sensor`, `ip`, `box_id` |
| 屏幕 | `screen_on`, `screen_off`, `screen_invert`, `screen_normal` |
| 设置 | `contrast`, `set_interval` |
| 帮助 | `help` |

## 数字孪生

访问 `/twin` 进入 3D 房屋场景（2室1厅1卫）：
- **3D 家具**：床、沙发、茶几、电视、马桶、洗手台、淋浴间
- **实时联动**：每 1 秒轮询设备状态，LED 开/关 → 灯光球高亮 + 地板光晕 + 点光源
- **PIR 脉冲**：有人检测 → 传感器红色脉冲缩放动画
- **直接控制**：每个房间灯有独立开关按钮，点击秒响应
- **操作**：鼠标旋转/缩放，按键 1 俯视 2 正面 3 侧面 0 默认

## 数据报表说明

- 折线图：最近 2 小时操作趋势
- 柱状图：设备活跃度 TOP10
- 饼图：操作类型分布
- 操作日志表格：20 条/页

每 10 秒自动刷新。

## GitHub

[https://github.com/Kobe-tech-space/AIoT](https://github.com/Kobe-tech-space/AIoT)
