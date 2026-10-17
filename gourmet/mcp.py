"""Read-only McDonald's MCP client. Credentials and raw responses stay local."""

from . import __version__
import json
import os
import urllib.error
import urllib.request

ENDPOINT = "https://mcp.mcd.cn"
READ_TOOLS = frozenset({
    "query-nearby-stores", "query-meals", "query-meal-detail",
    "query-store-coupons", "list-nutrition-foods", "calculate-price",
    "query-my-account", "query-my-coupons", "available-coupons",
    "mall-points-products", "mall-product-detail",
    "delivery-query-addresses", "delivery-query-stores",
    # 复购入口「跟上次一样」只读历史订单；官方 order-list/query-order 均为只读工具。
    # 只复用门店与商品编码，一律按当次价重新核价。
    "order-list", "query-order",
})


class MCPError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise MCPError("拒绝重定向：不向其他地址发送凭证。")


def decode_message(raw, content_type, request_id):
    if "text/event-stream" in content_type:
        # Read SSE event data; a notification may precede the actual response.
        for event in raw.replace("\r\n", "\n").split("\n\n"):
            data = "\n".join(line[5:].lstrip() for line in event.splitlines()
                             if line.startswith("data:"))
            if not data:
                continue
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict) and message.get("id") == request_id:
                return message
        raise MCPError("SSE 中没有匹配的响应。")
    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        raise MCPError("服务返回非 JSON 内容。") from None
    if not isinstance(message, dict) or message.get("id") != request_id:
        raise MCPError("MCP 响应 ID 不匹配。")
    return message


def tool_data(result):
    if not isinstance(result, dict) or result.get("isError"):
        raise MCPError("MCP 工具调用失败；未把错误当作餐品数据。")
    value = result.get("structuredContent")
    if value is None:
        for part in result.get("content", []):
            if part.get("type") == "text":
                try:
                    value = json.loads(part["text"])
                    break
                except (ValueError, KeyError):
                    continue
    if not isinstance(value, (dict, list)):
        raise MCPError("工具结果中没有可解析的结构化数据。")
    if isinstance(value, dict):
        if value.get("code") not in (None, 0, "0", 200, "200") or value.get("success") is False:
            if value.get('code') == 600057:
                raise MCPError('门店可能已关闭或不在营业时间；请主动选择营业门店，未自动换店。')
            detail = value.get('message') or value.get('msg')
            code = value.get('code')
            if isinstance(detail, str) and detail.strip():
                raise MCPError('麦当劳业务接口返回失败（code=%s）：%s；本轮已停止。' % (code, detail.strip()[:120]))
            raise MCPError("麦当劳业务接口返回失败；本轮已停止。")
        return value.get("data", value)
    return value


class Client:
    def __init__(self, token=None, max_response_bytes=8_000_000):
        if type(max_response_bytes) is not int or not 1_000_000 <= max_response_bytes <= 64_000_000:
            raise ValueError('响应上限须为 1～64 MB。')
        self.max_response_bytes = max_response_bytes
        self.token = token or os.environ.get("MCD_MCP_TOKEN", "")
        if not self.token or "\n" in self.token or "\r" in self.token:
            raise MCPError("请在本机设置 MCD_MCP_TOKEN 环境变量，不要公开 Token。")
        self.opener = urllib.request.build_opener(NoRedirect())
        self.session = None
        self.protocol = "2025-03-26"
        self.counter = 0
        self.schemas = {}

    def request(self, method, params=None, notification=False):
        self.counter += 1
        payload = {"jsonrpc": "2.0", "method": method}
        if not notification:
            payload["id"] = self.counter
        if params is not None:
            payload["params"] = params
        headers = {"Authorization": "Bearer " + self.token,
                   "Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream",
                   "MCP-Protocol-Version": self.protocol}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        req = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(), headers=headers)
        try:
            with self.opener.open(req, timeout=30) as response:
                session = response.headers.get("Mcp-Session-Id")
                if session:
                    self.session = session
                raw = response.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise MCPError("响应超过配置上限；本轮已停止，未使用截断数据。可用 --max-response-mb 调整。")
                content_type = response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            raise MCPError("MCP HTTP %s；请检查凭证、参数或稍后重试。" % exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise MCPError("无法连接麦当劳 MCP；没有回退到示例数据。") from None
        if notification:
            return None
        message = decode_message(raw.decode("utf-8"), content_type, payload["id"])
        if "error" in message or "result" not in message:
            raise MCPError("MCP 协议返回错误；本轮已停止。")
        return message["result"]

    def initialize(self):
        result = self.request("initialize", {
            "protocolVersion": self.protocol, "capabilities": {},
            "clientInfo": {"name": "mcd-agent-gourmet", "version": __version__},
        })
        self.protocol = result.get("protocolVersion", self.protocol)
        self.request("notifications/initialized", notification=True)

    def tools(self):
        self.initialize()
        result = self.request("tools/list", {})
        for tool in result.get("tools", []):
            if tool.get("name") in READ_TOOLS:
                self.schemas[tool["name"]] = tool.get("inputSchema", {})
        return self.schemas

    def call(self, name, arguments):
        if name not in READ_TOOLS:
            raise MCPError("本版本仅允许查询和核价，不允许下单、领券、支付等写操作。")
        if not isinstance(arguments, dict):
            raise MCPError("工具参数必须是 JSON 对象。")
        if not self.schemas:
            self.tools()
        if name not in self.schemas:
            raise MCPError("当前服务没有提供请求的工具。")
        missing = set(self.schemas[name].get("required", [])) - arguments.keys()
        if missing:
            raise MCPError("工具缺少必填字段：" + ", ".join(sorted(missing)))
        # Stateless servers may not retain initialization between calls.
        if not self.session:
            self.initialize()
        return tool_data(self.request("tools/call", {"name": name, "arguments": arguments}))
