"""Small read-only Streamable HTTP client. Token comes only from the environment."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://mcp.mcd.cn"
READ_ONLY = frozenset({
    "query-nearby-stores", "query-meals", "query-meal-detail",
    "query-store-coupons", "list-nutrition-foods", "calculate-price",
    "now-time-info",
})


class MCPError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise MCPError("服务返回重定向，已停止请求。")


def decode_response(body, request_id):
    try:
        messages = [json.loads(body)]
    except json.JSONDecodeError:
        messages = []
        # SSE data may span lines. Only complete events are decoded.
        for event in body.replace("\r\n", "\n").split("\n\n"):
            data = "\n".join(line[5:].lstrip(" ") for line in event.splitlines()
                             if line.startswith("data:"))
            if data:
                try:
                    messages.append(json.loads(data))
                except json.JSONDecodeError:
                    continue
    for message in messages:
        if isinstance(message, dict) and message.get("id") == request_id:
            if "error" in message:
                raise MCPError("MCP 协议错误，code=" + str(message["error"].get("code")))
            if "result" in message:
                return message["result"]
    raise MCPError("没有收到对应请求的 MCP 结果。")


class Client:
    def __init__(self, token):
        self.headers = {"Authorization": "Bearer " + token,
                        "Accept": "application/json, text/event-stream",
                        "Content-Type": "application/json"}
        self.opener = urllib.request.build_opener(NoRedirect())
        self.next_id = 0

    def request(self, method, params=None, notification=False):
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notification:
            self.next_id += 1
            payload["id"] = self.next_id
        request = urllib.request.Request(ENDPOINT,
                                        data=json.dumps(payload).encode("utf-8"),
                                        headers=self.headers, method="POST")
        try:
            with self.opener.open(request, timeout=30) as response:
                session = response.headers.get("Mcp-Session-Id")
                if session:
                    self.headers["Mcp-Session-Id"] = session
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise MCPError(f"MCP HTTP {exc.code}；检查认证、限流或输入。") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise MCPError("MCP 网络请求失败；未输出请求凭证。") from None
        if notification:
            return None
        return decode_response(body, payload["id"])

    def initialize(self):
        result = self.request("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "mcd-budget", "version": "0.1.0"},
        })
        self.headers["MCP-Protocol-Version"] = result["protocolVersion"]
        self.request("notifications/initialized", notification=True)
        return result

    def call(self, name, arguments):
        if name not in READ_ONLY:
            raise MCPError("本客户端只支持预算搭配所需的只读工具。")
        if not isinstance(arguments, dict):
            raise MCPError("工具输入必须是 JSON 对象。")
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise MCPError("工具调用失败；没有生成可用报价。")
        return result


def business_response(result):
    """Extract official JSON embedded in text, or structuredContent."""
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        parsed = structured
    else:
        parsed = None
        for block in result.get("content", []):
            if block.get("type") != "text":
                continue
            value = block.get("text", "")
            if "## Original Response" in value:
                value = value.split("## Original Response", 1)[1]
            # Some servers wrap JSON with a markdown fence.
            start = value.find("{")
            if start >= 0:
                try:
                    parsed, _ = json.JSONDecoder().raw_decode(value[start:])
                    break
                except json.JSONDecodeError:
                    continue
    if not isinstance(parsed, dict):
        raise MCPError("无法解析业务响应，请检查当前工具返回格式。")
    if parsed.get("success") is False or ("code" in parsed and parsed["code"] != 200):
        raise MCPError("业务查询失败；没有生成可用报价。")
    return parsed


def main():
    parser = argparse.ArgumentParser(description="麦麦预算搭配师只读 MCP 客户端")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tools")
    call = sub.add_parser("call")
    call.add_argument("tool", choices=sorted(READ_ONLY))
    call.add_argument("--input", help="UTF-8 JSON 参数文件")
    args = parser.parse_args()
    token = os.environ.get("MCD_MCP_TOKEN")
    if not token:
        parser.exit(2, "请在环境变量 MCD_MCP_TOKEN 中配置凭证。\n")
    try:
        client = Client(token)
        client.initialize()
        if args.command == "tools":
            result = client.request("tools/list", {})
        else:
            arguments = {}
            if args.input:
                with open(args.input, encoding="utf-8-sig") as file:
                    arguments = json.load(file)
            result = business_response(client.call(args.tool, arguments))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (MCPError, ValueError, OSError) as exc:
        # Error bodies and paths could contain personal information.
        message = str(exc) if isinstance(exc, MCPError) else "输入文件不可读或格式错误。"
        parser.exit(2, message + "\n")


if __name__ == "__main__":
    main()
