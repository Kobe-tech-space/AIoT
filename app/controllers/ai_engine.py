# 模型引擎 + 接口管理 Controller

import json
import os
import urllib.request
from app.controllers.base import BaseHandler
from app.controllers.user_manage import admin_required
from app.models.ai_model import AiModelRepository
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


class ModelChatStreamHandler(BaseHandler):
    """对话（带上下文）"""

    @admin_required
    def post(self):
        model_id = int(self.get_body_argument("id"))
        prompt = (self.get_body_argument("prompt", "") or "").strip()
        history_json = (self.get_body_argument("history", "[]") or "[]").strip()

        model = AiModelRepository.get_model_by_id(model_id)
        if not model:
            self.write(json.dumps({"code": 1, "msg": "模型不存在"}, ensure_ascii=False))
            return

        try:
            history = json.loads(history_json)
        except:
            history = []

        messages = [{"role": "system", "content": _load_system_prompt()}]
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        try:
            req_data = json.dumps({
                "model": model["model_name"],
                "messages": messages,
                "temperature": model["temperature"],
                "max_tokens": model["max_tokens"],
            }).encode("utf-8")

            req = urllib.request.Request(model["api_url"] + "/chat/completions", data=req_data)
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {model['api_key']}")

            resp = urllib.request.urlopen(req, timeout=60)
            body = json.loads(resp.read().decode("utf-8"))
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


# ==================== 工具函数 ====================

def mask_key(key):
    if not key or len(key) < 8:
        return key
    return key[:5] + "***" + key[-3:]
