"""只查询已录入知识库，验证订单知识库、订单适配器和 unknown 路由。"""

import json
import urllib.error
import urllib.request

BASE = "http://localhost:8000"


def request(method: str, path: str, payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        raw = error.read().decode(errors="replace")
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, {"detail": raw}


status, login = request("POST", "/auth/login", {"username": "kb_test_admin", "password": "KbTest2026!"})
if status != 200:
    raise SystemExit(f"登录失败: HTTP {status} {login}")
token = login["access_token"]
print("登录成功")

status, documents = request("GET", "/documents", token=token)
print(f"知识库文档: HTTP {status}，共 {len(documents) if isinstance(documents, list) else 0} 篇")

queries = [
    ("退换货流程是什么", "knowledge"),
    ("支付方式有哪些", "knowledge"),
    ("修改收货地址怎么操作", "knowledge"),
    ("查询订单 ORD-20240701-0001 的物流", "order"),
    ("你好", "unknown"),
]

passed = 0
for query, expected in queries:
    status, result = request("POST", "/chat", {"query": query}, token=token)
    if status != 200:
        print(f"❌ {query} → HTTP {status}: {result}")
        continue
    actual = result.get("intent")
    answer = result.get("answer", "").replace("\n", " ")[:160]
    has_sources = bool(result.get("sources"))
    ok = actual == expected and (expected != "knowledge" or has_sources)
    if ok:
        passed += 1
    mark = "✅" if ok else "❌"
    print(f"{mark} 问题: {query}")
    print(f"   期望意图={expected}，实际意图={actual}，来源数={len(result.get('sources', []))}")
    print(f"   回答: {answer}")

print(f"\n验证结果: {passed}/{len(queries)} 通过")
if passed != len(queries):
    raise SystemExit(1)
