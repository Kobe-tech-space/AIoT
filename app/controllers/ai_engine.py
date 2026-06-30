# 模型引擎 + 接口管理 Controller

import json
import os
import urllib.request
from app.controllers.base import BaseHandler, MobileBaseHandler
from app.controllers.user_manage import admin_required
from app.models.ai_model import AiModelRepository
from app.models.db import get_connection
from app.models.external_api import ExternalApiRepository

# 加载机器人提示词
def _load_system_prompt():
    # CDUTAgentOS/app/controllers/ai_engine.py -> CDUTAgentOS/skills/robotTools.md
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    prompt_path = os.path.join(base, "skills", "robotTools.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""


# ==================== 模型引擎 ====================

class ModelListHandler(BaseHandler):
    """模型管理页面"""

    @admin_required
    def get(self):
        self.render("model_list.html", title="模型引擎")


class ModelApiHandler(BaseHandler):
    """模型 API"""

    @admin_required
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 6))
        keyword = self.get_argument("keyword", "")

        rows, total = AiModelRepository.list_models(page, limit, keyword)
        data = []
        for r in rows:
            data.append({
                "id": r["id"], "name": r["name"], "api_key": mask_key(r["api_key"]),
                "api_url": r["api_url"], "model_name": r["model_name"],
                "temperature": r["temperature"], "max_tokens": r["max_tokens"],
                "is_default": r["is_default"], "created_at": r["created_at"],
            })

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({"code": 0, "count": total, "data": data}, ensure_ascii=False))

    @admin_required
    def post(self):
        name = (self.get_body_argument("name", "") or "").strip()
        api_key = (self.get_body_argument("api_key", "") or "").strip()
        api_url = (self.get_body_argument("api_url", "") or "").strip()
        model_name = (self.get_body_argument("model_name", "") or "").strip()
        temperature = float(self.get_body_argument("temperature", "0.7"))
        max_tokens = int(self.get_body_argument("max_tokens", "2048"))

        if not name:
            self.write(json.dumps({"code": 1, "msg": "名称不能为空"}, ensure_ascii=False))
            return

        AiModelRepository.create_model(name, api_key, api_url, model_name, temperature, max_tokens)
        self.write(json.dumps({"code": 0, "msg": "添加成功"}, ensure_ascii=False))

    @admin_required
    def put(self):
        model_id = int(self.get_body_argument("id"))
        kwargs = {}
        for field in ["name", "api_key", "api_url", "model_name"]:
            val = (self.get_body_argument(field, "") or "").strip()
            if val:
                # 如果 api_key 是掩码形式，不更新
                if field == "api_key" and val.startswith("sk-***"):
                    continue
                kwargs[field] = val
        kwargs["temperature"] = float(self.get_body_argument("temperature", "0.7"))
        kwargs["max_tokens"] = int(self.get_body_argument("max_tokens", "2048"))
        AiModelRepository.update_model(model_id, **kwargs)
        self.write(json.dumps({"code": 0, "msg": "修改成功"}, ensure_ascii=False))

    @admin_required
    def delete(self):
        model_id = int(self.get_body_argument("id"))
        AiModelRepository.delete_model(model_id)
        self.write(json.dumps({"code": 0, "msg": "删除成功"}, ensure_ascii=False))


class ModelDefaultHandler(BaseHandler):
    """设为默认模型"""

    @admin_required
    def post(self):
        model_id = int(self.get_body_argument("id"))
        AiModelRepository.set_default(model_id)
        self.write(json.dumps({"code": 0, "msg": "已设为默认模型"}, ensure_ascii=False))


class ModelChatHandler(BaseHandler):
    """模型对话测试"""

    @admin_required
    def post(self):
        model_id = int(self.get_body_argument("id"))
        prompt = (self.get_body_argument("prompt", "") or "").strip()

        model = AiModelRepository.get_model_by_id(model_id)
        if not model:
            self.write(json.dumps({"code": 1, "msg": "模型不存在"}, ensure_ascii=False))
            return

        try:
            req_data = json.dumps({
                "model": model["model_name"],
                "messages": [
                    {"role": "system", "content": _load_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                "temperature": model["temperature"],
                "max_tokens": model["max_tokens"],
            }).encode("utf-8")

            req = urllib.request.Request(model["api_url"] + "/chat/completions", data=req_data)
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {model['api_key']}")

            resp = urllib.request.urlopen(req, timeout=30)
            body = json.loads(resp.read().decode("utf-8"))
            reply = body["choices"][0]["message"]["content"]
            self.write(json.dumps({"code": 0, "reply": reply}, ensure_ascii=False))
        except Exception as e:
            self.write(json.dumps({"code": 1, "msg": f"调用失败: {e}"}, ensure_ascii=False))


class ModelChatPageHandler(BaseHandler):
    """对话页面"""

    @admin_required
    def get(self):
        model_id = self.get_argument("id", "")
        self.render("chat.html", title="AI 对话", model_id=model_id)


# ==================== Function Calling ====================

TOOLS = [
    {"type":"function","function":{"name":"get_weather","description":"查询指定城市的当前天气","parameters":{"type":"object","properties":{"city":{"type":"string","description":"城市名，如成都"}},"required":["city"]}}},
    {"type":"function","function":{"name":"control_device","description":"向AIoT设备下发控制指令","parameters":{"type":"object","properties":{"box_id":{"type":"string","description":"设备编号"},"cmd":{"type":"string","enum":["on","off","auto","manual","status","screen_on","screen_off"]}},"required":["box_id","cmd"]}}},
    {"type":"function","function":{"name":"get_device_status","description":"查询AIoT设备的在线状态和传感器数据","parameters":{"type":"object","properties":{"box_id":{"type":"string","description":"设备编号，留空查全部"}}}}}
]

def execute_function(name, args):
    if name == "get_weather":
        city = args.get("city", "chengdu")
        try:
            req = urllib.request.Request(f"https://wttr.in/{city}?format=j1")
            req.add_header("User-Agent", "curl/7.0")
            resp = urllib.request.urlopen(req, timeout=8)
            data = json.loads(resp.read().decode("utf-8"))
            cur = data.get("current_condition", [{}])[0]
            w = cur.get("weatherDesc", [{}])[0].get("value", "?")
            t = cur.get("temp_C", "?")
            h = cur.get("humidity", "?")
            return f"{city}天气：{w}，{t}C，湿度{h}%"
        except Exception as e:
            return f"天气查询失败: {e}"
    elif name == "get_device_status":
        from app.controllers.server_manager import get_online_devices
        devices = get_online_devices()
        box_id = args.get("box_id", "")
        if not devices: return "当前没有在线设备"
        if box_id:
            dev = devices.get(box_id)
            if not dev: return f"设备 {box_id} 不在线"
            s = dev.get("status", {})
            return f"{box_id}: LED={'ON' if s.get('led') else 'OFF'}, 模式={s.get('mode','?')}, 光敏={'暗' if s.get('light') else '亮'}, 人体={'有人' if s.get('pir') else '无人'}"
        lines = [f"{bid}: LED={'ON' if d.get('status',{}).get('led') else 'OFF'}, 模式={d.get('status',{}).get('mode','?')}" for bid,d in devices.items()]
        return chr(10).join(lines)
    elif name == "control_device":
        from app.controllers.server_manager import send_device_command, _running_servers
        if not _running_servers: return "没有运行中的服务器"
        sid = list(_running_servers.keys())[0]
        ok = send_device_command(sid, args.get("box_id",""), args.get("cmd",""))
        return f"指令 {args.get('cmd','')} {'已发送' if ok else '失败'}"
    return "未知操作"


class ModelChatStreamHandler(MobileBaseHandler):
    """对话（带上下文）— 移动端免 XSRF"""

    def post(self):
        model_id = int(self.get_body_argument("id"))
        prompt = (self.get_body_argument("prompt", "") or "").strip()
        history_json = (self.get_body_argument("history", "[]") or "[]").strip()
        model = AiModelRepository.get_model_by_id(model_id)
        if not model:
            self.write(json.dumps({"code": 1, "msg": "模型不存在"}, ensure_ascii=False)); return
        try: history = json.loads(history_json)
        except: history = []

        # 快控优先：本地关键词 → 直接执行，秒响应
        t = prompt.lower()
        func_result = None
        if any(kw in t for kw in ['天气','weather','气温','下雨']):
            city = 'chengdu'
            for c in ['成都','北京','上海','深圳','杭州','南京','武汉','重庆','西安','广州']:
                if c in prompt: city = c; break
            func_result = execute_function('get_weather', {'city': city})
        elif any(kw in t for kw in ['设备状态','传感器','在线设备','查设备','还有什么设备','设备列表']):
            func_result = execute_function('get_device_status', {})
        elif any(kw in t for kw in ['开灯','关灯','自动','手动','亮屏','息屏','打开灯','关闭灯','切换']):
            # 指令已在移动端/前端关键词检测中处理，这里做兜底
            pass

        if func_result:
            # 用模型润色：将结果包装成口语化回复
            fm = [{"role":"system","content":"你是小智。把以下数据用口语化方式告诉用户，1-2句话，带emoji。"},
                  {"role":"user","content": "用户问：" + prompt + " 查询结果：" + func_result + " 请自然回复："}]
            try:
                rd = json.dumps({"model":model["model_name"],"messages":fm,"temperature":0.8,"max_tokens":200}).encode("utf-8")
                rq = urllib.request.Request(model["api_url"]+"/chat/completions",data=rd)
                rq.add_header("Content-Type","application/json")
                rq.add_header("Authorization",f"Bearer {model['api_key']}")
                rr = json.loads(urllib.request.urlopen(rq,timeout=15).read().decode("utf-8"))
                reply = rr["choices"][0]["message"]["content"]
            except:
                reply = func_result
            self.write(json.dumps({"code": 0, "reply": reply}, ensure_ascii=False))
            return

        # 模型兜底：复杂语义走大模型
        messages = [{"role": "system", "content": _load_system_prompt()}]
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        try:
            req_data = json.dumps({"model": model["model_name"], "messages": messages, "temperature": model["temperature"], "max_tokens": model["max_tokens"]}).encode("utf-8")
            req = urllib.request.Request(model["api_url"] + "/chat/completions", data=req_data)
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {model['api_key']}")
            body = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
            reply = body["choices"][0]["message"]["content"]
            self.write(json.dumps({"code": 0, "reply": reply}, ensure_ascii=False))
        except Exception as e:
            self.write(json.dumps({"code": 1, "msg": f"调用失败: {e}"}, ensure_ascii=False))


# ==================== 接口管理 ====================

class ApiListHandler(BaseHandler):
    """接口管理页面"""

    @admin_required
    def get(self):
        self.render("api_list.html", title="接口管理")


class ExternalApiHandler(BaseHandler):
    """接口管理 API"""

    @admin_required
    def get(self):
        page = int(self.get_argument("page", 1))
        limit = int(self.get_argument("limit", 20))
        keyword = self.get_argument("keyword", "")

        rows, total = ExternalApiRepository.list_apis(page, limit, keyword)
        data = []
        for r in rows:
            data.append({
                "id": r["id"], "name": r["name"], "api_type": r["api_type"],
                "url": r["url"], "api_key": mask_key(r["api_key"]),
                "params": r["params"], "status": r["status"],
                "created_at": r["created_at"],
            })

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({"code": 0, "count": total, "data": data}, ensure_ascii=False))

    @admin_required
    def post(self):
        name = (self.get_body_argument("name", "") or "").strip()
        api_type = (self.get_body_argument("api_type", "") or "").strip()
        url = (self.get_body_argument("url", "") or "").strip()
        api_key = (self.get_body_argument("api_key", "") or "").strip()
        params = (self.get_body_argument("params", "{}") or "{}").strip()

        if not name or not url:
            self.write(json.dumps({"code": 1, "msg": "名称和地址不能为空"}, ensure_ascii=False))
            return

        ExternalApiRepository.create_api(name, api_type, url, api_key, params)
        self.write(json.dumps({"code": 0, "msg": "添加成功"}, ensure_ascii=False))

    @admin_required
    def put(self):
        api_id = int(self.get_body_argument("id"))
        kwargs = {}
        for field in ["name", "api_type", "url", "params"]:
            val = (self.get_body_argument(field, "") or "").strip()
            if val:
                kwargs[field] = val
        key_val = (self.get_body_argument("api_key", "") or "").strip()
        if key_val and not key_val.startswith("sk-***"):
            kwargs["api_key"] = key_val
        ExternalApiRepository.update_api(api_id, **kwargs)
        self.write(json.dumps({"code": 0, "msg": "修改成功"}, ensure_ascii=False))

    @admin_required
    def delete(self):
        api_id = int(self.get_body_argument("id"))
        ExternalApiRepository.delete_api(api_id)
        self.write(json.dumps({"code": 0, "msg": "删除成功"}, ensure_ascii=False))


class ApiTestHandler(BaseHandler):
    """连通性测试"""

    @admin_required
    def post(self):
        api_id = int(self.get_body_argument("id"))
        api = ExternalApiRepository.get_api_by_id(api_id)
        if not api:
            self.write(json.dumps({"code": 1, "msg": "接口不存在"}, ensure_ascii=False))
            return

        try:
            req = urllib.request.Request(api["url"])
            req.add_header("Content-Type", "application/json")
            if api["api_key"]:
                req.add_header("Authorization", f"Bearer {api['api_key']}")
            resp = urllib.request.urlopen(req, timeout=10)
            body = resp.read().decode("utf-8")[:500]
            self.write(json.dumps({
                "code": 0,
                "msg": f"连通成功 (HTTP {resp.status})",
                "body": body,
            }, ensure_ascii=False))
        except Exception as e:
            self.write(json.dumps({"code": 1, "msg": f"连通失败: {e}"}, ensure_ascii=False))


class TTSHandler(MobileBaseHandler):
    """语音合成代理（qwen3-tts-flash）— 不支持流式，返回完整 MP3"""

    def post(self):
        model_id = self.get_body_argument("id", "1")
        text = (self.get_body_argument("text", "") or "").strip()

        model = AiModelRepository.get_model_by_id(int(model_id))
        # 优先用 TTS 专用模型，否则查 ai_models 中 model_name 含 tts 的
        if not model or "tts" not in (model["model_name"] or "").lower():
            with get_connection() as conn:
                model = conn.execute(
                    "SELECT * FROM ai_models WHERE LOWER(model_name) LIKE '%tts%' LIMIT 1"
                ).fetchone()
        if not model:
            model = AiModelRepository.get_default_model()
        if not model:
            self.set_status(500)
            self.write(json.dumps({"code": 1, "msg": "没有可用的 TTS 模型"}, ensure_ascii=False))
            return

        try:
            req_data = json.dumps({
                "model": "qwen3-tts-flash",
                "input": text,
                "voice": "longxiaochun_v3",
                "response_format": "mp3",
            }).encode("utf-8")

            req = urllib.request.Request(model["api_url"] + "/audio/speech", data=req_data)
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {model['api_key']}")

            resp = urllib.request.urlopen(req, timeout=30)
            audio_data = resp.read()

            self.set_header("Content-Type", "audio/mpeg")
            self.set_header("Content-Length", str(len(audio_data)))
            self.write(audio_data)
        except Exception as e:
            self.set_status(500)
            detail = str(e)
            try:
                if hasattr(e, "read"): detail = e.read().decode("utf-8")[:500]
            except: pass
            self.write(json.dumps({"code": 1, "msg": f"TTS 失败: {detail}"}, ensure_ascii=False))


class WeatherProxyHandler(MobileBaseHandler):
    """天气接口代理（wttr.in）— 移动端免 XSRF"""

    def get(self):
        city = self.get_argument("city", "chengdu")
        try:
            url = f"https://wttr.in/{city}?format=j1"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "curl/7.0")
            resp = urllib.request.urlopen(req, timeout=10)
            body = resp.read().decode("utf-8")
            self.set_header("Content-Type", "application/json")
            self.write(body)
        except Exception as e:
            self.write(json.dumps({"code": 1, "msg": f"天气查询失败: {e}"}, ensure_ascii=False))


# ==================== 工具函数 ====================

def mask_key(key):
    if not key or len(key) < 8:
        return key
    return key[:5] + "***" + key[-3:]
