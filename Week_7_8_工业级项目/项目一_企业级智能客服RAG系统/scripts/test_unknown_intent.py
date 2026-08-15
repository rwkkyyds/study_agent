"""录入订单相关知识库 → 测试知识库查询 + 意图分类。

流程：
1. 登录 admin 账号
2. 录入订单相关文档（物流政策、退换货流程、发货时间、售后政策、支付方式）
3. 测试知识库命中（订单相关问题）
4. 测试意图分类正确性（知识库/订单/人工/unknown）
"""

import json
import urllib.request
import urllib.parse
import time

BASE = "http://localhost:8000"
AUTH = {"Content-Type": "application/json"}


def api(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def upload_doc(title, content, token):
    params = urllib.parse.urlencode({"title": title, "content": content})
    req = urllib.request.Request(
        f"{BASE}/documents/upload?{params}",
        data=b"",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


# ======== 1. 登录 admin ========
print("=" * 60)
print("1. 登录 admin")
status, data = api("POST", "/auth/login", {"username": "kb_test_admin", "password": "KbTest2026!"})
assert status == 200, f"登录失败: {data}"
token = data["access_token"]
print(f"   ✅ 登录成功 token={token[:20]}...")

# ======== 2. 清理旧文档（可选） ========
print("\n2. 查看已有文档")
status, docs = api("GET", "/documents", token=token)
print(f"   当前文档数: {len(docs)}")

# ======== 3. 录入订单相关文档 ========
print("\n" + "=" * 60)
print("3. 录入订单相关知识库文档")
print("=" * 60)

order_docs = [
    {
        "title": "物流配送政策",
        "content": """物流配送政策

一、配送范围
本平台支持全国范围（含港澳台）的物流配送服务。部分偏远地区配送时间可能延长1-2个工作日。

二、配送时效
1. 标准配送：下单后3-5个工作日送达，满99元免运费。
2. 加急配送：下单后1-2个工作日送达，需额外支付20元加急费。
3. 当日达：仅限北京、上海、广州、深圳、杭州、成都等一二线城市主城区，下单时间需在当日12:00前。

三、物流查询
用户可在「我的订单」页面查看物流状态，或通过订单号联系在线客服查询。

四、签收注意事项
1. 请先验货再签收，如发现商品破损或缺失，可直接拒收并联系客服。
2. 签收后48小时内可申请售后（质量问题除外）。""",
    },
    {
        "title": "退换货政策",
        "content": """退换货政策

一、7天无理由退货
自签收之日起7天内，商品保持原状（未拆封、未使用、不影响二次销售），可申请无理由退货。

二、15天质量问题换货
自签收之日起15天内，如商品出现质量问题，可申请免费换货。运费由平台承担。

三、退换货流程
1. 登录账号 → 进入「我的订单」→ 选择需要退换的商品 → 点击「申请售后」
2. 填写退换货原因并上传凭证（照片/视频）
3. 审核通过后，将商品寄回指定地址
4. 仓库收到商品后3个工作日内完成退款或换货发货

四、退款到账时间
1. 支付宝/微信支付：审核通过后1-3个工作日原路退回
2. 银行卡支付：审核通过后3-7个工作日退回
3. 余额支付：审核通过后即时到账

五、以下情况不支持退换货
1. 已拆封的软件、音像制品、虚拟商品
2. 超过退换货期限
3. 商品已使用或人为损坏""",
    },
    {
        "title": "发货时间说明",
        "content": """发货时间说明

一、现货商品
1. 工作日下单：当日16:00前付款的订单，当天发货；16:00后付款的订单，次日发货。
2. 周末及节假日：订单统一顺延至下一个工作日发货。

二、预售商品
以商品详情页标注的发货时间为准，通常为付款后7-15个工作日内发货。

三、定制商品
定制商品需额外3-5个工作日制作时间，发货前客服会主动联系确认。

四、缺货/延迟通知
如遇库存不足或物流异常，平台将在24小时内通过短信和站内信通知用户，并提供以下解决方案：
1. 免费更换同等价位的其他商品
2. 取消订单并全额退款
3. 等待补货（预计3-7个工作日）""",
    },
    {
        "title": "售后服务政策",
        "content": """售后服务政策

一、保修政策
1. 电子类商品：整机保修1年，主要部件（如主板、屏幕）保修2年
2. 家电类商品：整机保修3年，压缩机等重要部件保修5年
3. 服装鞋帽类：非人为损坏的质量问题，30天内可申请维修或换货

二、维修服务
1. 全国联保：凭订单号可在任何一家授权维修点享受保修服务
2. 上门取件：保修期内质量问题，平台提供免费上门取件服务
3. 维修周期：一般维修7-15个工作日完成

三、投诉与建议
如对服务不满意，可拨打客服热线 400-888-8888 或输入「转人工」联系在线客服。

四、差价保护
1. 购买后7天内如商品降价，可申请差价补偿
2. 大促期间（双11、618等）不参与差价保护""",
    },
    {
        "title": "支付方式说明",
        "content": """支付方式说明

一、支持的支付方式
1. 支付宝（余额、花呗、信用卡）
2. 微信支付（零钱、信用卡、借记卡）
3. 银联支付（支持所有银联卡）
4. 平台余额支付
5. 企业转账（对公账户，需联系销售确认）

二、分期付款
1. 花呗分期：支持3期、6期、12期，部分商品享免息
2. 信用卡分期：支持3期、6期、12期、24期

三、发票说明
1. 电子发票：下单时填写发票信息，随订单完成自动发送至邮箱
2. 纸质发票：需额外3-5个工作日寄出，免运费
3. 企业发票：需提供企业名称、税号、开户行及账号信息""",
    },
    {
        "title": "订单取消与修改",
        "content": """订单取消与修改

一、取消订单
1. 未支付订单：可在「我的订单」页面直接取消
2. 已支付未发货订单：可在「我的订单」页面申请取消，款项将在1-3个工作日内退回
3. 已发货订单：需联系客服处理，商品拒收或退回后办理退款

二、修改订单
1. 修改地址：发货前可在「我的订单」页面修改收货地址
2. 修改商品：已支付订单不支持直接修改商品，建议取消后重新下单
3. 修改数量：未支付订单可取消后重新下单

三、订单合并与拆分
目前暂不支持订单合并与拆分功能，如有需要请联系客服协助处理。""",
    },
]

uploaded = 0
for doc in order_docs:
    status, data = upload_doc(doc["title"], doc["content"], token)
    if status == 201:
        uploaded += 1
        print(f"   ✅ [{status}] {doc['title']} → id={data['id']} chunks={data['chunks']}")
    else:
        print(f"   ❌ [{status}] {doc['title']} → {data}")
    time.sleep(0.1)  # 避免过快请求

print(f"\n   共上传 {uploaded}/{len(order_docs)} 篇文档")

# 等待向量库更新
print("\n   等待向量库索引更新...")
time.sleep(1)

# ======== 4. 测试订单相关查询 ========
print("\n" + "=" * 60)
print("4. 测试知识库查询（订单相关问题）")
print("=" * 60)

order_queries = [
    "发货后多久能到",
    "退换货流程是什么",
    "怎么申请退款",
    "支付方式有哪些",
    "修改收货地址怎么操作",
    "保修期多久",
    "什么时候发货",
    "可以开发票吗",
]

for q in order_queries:
    status, data = api("POST", "/chat", {"query": q}, token=token)
    if status == 200:
        intent = data["intent"]
        answer = data["answer"][:120]
        print(f"\n   Q: {q}")
        print(f"   意图: {intent} | 回答: {answer}...")
    else:
        print(f"\n   ❌ Q: {q} → {data}")

# ======== 5. 测试非订单查询 ========
print("\n" + "=" * 60)
print("5. 测试非订单类查询（确认意图分类正确）")
print("=" * 60)

other_queries = [
    ("你好", "unknown"),
    ("你是谁", "unknown"),
    ("今天天气怎么样", "unknown"),
    ("请转人工客服", "human"),
    ("我要投诉", "human"),
    ("查询订单 ORD-20240701-0001 的物流", "order"),
    ("退款进度", "order"),
]

for q, expected_intent in other_queries:
    status, data = api("POST", "/chat", {"query": q}, token=token)
    if status == 200:
        intent = data["intent"]
        answer = data["answer"][:120]
        match = "✅" if intent == expected_intent else "❌"
        print(f"\n   {match} Q: {q}")
        print(f"   期望={expected_intent} 实际={intent} | 回答: {answer}...")
    else:
        print(f"\n   ❌ Q: {q} → {data}")

# ======== 6. 查看知识库文档列表 ========
print("\n" + "=" * 60)
print("6. 知识库文档列表")
status, docs = api("GET", "/documents", token=token)
print(f"   共 {len(docs)} 篇文档:")
for d in docs:
    print(f"   - [{d['id']}] {d['title']} ({d['chunk_count']} chunks)")

print("\n" + "=" * 60)
print("全部测试完成 ✅")
print("=" * 60)