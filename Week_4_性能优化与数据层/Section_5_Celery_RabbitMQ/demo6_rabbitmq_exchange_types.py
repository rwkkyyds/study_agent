"""
demo6_rabbitmq_exchange_types.py — Exchange 类型实战

学习目标：
1. 理解 Exchange 是消息路由器，决定消息去哪个 Queue
2. 掌握三种 Exchange 类型：direct / topic / fanout
3. 理解 Binding = Exchange + Queue + Routing Key 的绑定关系
4. 看清 Celery 底层用的是哪种 Exchange（direct）

运行前先启动 RabbitMQ：
  终端1: docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
  终端2: python demo6_rabbitmq_exchange_types.py

浏览器打开 http://localhost:15672（账号 guest/guest）可实时看到 Exchange 和 Queue 的创建与消息流转。

安装依赖：pip install pika
"""

import time
import logging
import threading

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

import pika
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672


def get_channel():
    """快捷方法：建立连接并返回 channel"""
    params = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, heartbeat=0)
    connection = pika.BlockingConnection(params)
    return connection, connection.channel() # 返回连接和 channel，方便后续操作


# ================================================
# PART 1：Direct Exchange — 按 Routing Key 精确匹配
# ================================================
def demo_direct_exchange():
    """
    场景：日志分级路由
      error 级别 → error_queue（通知运维）
      info/warning 级别 → info_queue（存日志）

    Binding 规则：
      Exchange "logs_direct" + Queue "error_queue" + routing_key "error"
      Exchange "logs_direct" + Queue "info_queue"  + routing_key "info"
      Exchange "logs_direct" + Queue "info_queue"  + routing_key "warning"

    【Direct Exchange】routing_key 完全匹配才投递
    Celery 默认就用 Direct Exchange！
    """
    print("\n-- PART 1：Direct Exchange（精确匹配）--")
    print("""
  【Direct Exchange】日志路由示意：

                    +-------------+
  routing_key="error"|  error_queue | ← 消费 error 日志
                    +-------------+
                   /
  Producer -->  Exchange "logs_direct"
                   \\
                    +-------------+
  routing_key="info" |  info_queue  | ← 消费 info/warning 日志
  routing_key="warning"+-------------+
""")

    conn, ch = get_channel()

    EXCHANGE = "demo6_logs_direct"

    # Step 1：声明 Exchange
    # 【exchange_declare】exchange_type='direct' 精确匹配 routing_key
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)

    # Step 2：声明两个队列并绑定
    q1 = ch.queue_declare(queue="demo6_error_queue", durable=True).method.queue
    q2 = ch.queue_declare(queue="demo6_info_queue", durable=True).method.queue

    # 【queue_bind】绑定：把 Queue 连接到 Exchange 上，指定 routing_key
    ch.queue_bind(exchange=EXCHANGE, queue=q1, routing_key="error")
    ch.queue_bind(exchange=EXCHANGE, queue=q2, routing_key="info")
    ch.queue_bind(exchange=EXCHANGE, queue=q2, routing_key="warning")  # info_queue 也收 warning

    # Step 3：发送不同级别的日志
    logs = [
        ("error", "磁盘空间不足！"),    # → error_queue
        ("info", "服务启动成功"),        # → info_queue
        ("warning", "内存使用率 85%"),   # → info_queue（绑定了 warning key）
        ("debug", "请求参数：id=42"),    # → 无队列匹配，消息被丢弃！
    ]
    for level, msg in logs:
        ch.basic_publish(
            exchange=EXCHANGE,
            routing_key=level,
            body=f"[{level.upper()}] {msg}",
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
            ),
        )
        logger.info(f"  [Producer] routing_key='{level}' → '{msg}'")

    # Step 4：消费 error_queue
    method, _, body = ch.basic_get(queue=q1, auto_ack=True)
    if method:
        logger.info(f"  [error_queue 收到] {body.decode()}")

    # Step 5：消费 info_queue（应该有 2 条）
    for _ in range(2):
        method, _, body = ch.basic_get(queue=q2, auto_ack=True)
        if method:
            logger.info(f"  [info_queue 收到]  {body.decode()}")

    conn.close()
    print("\n  > 注意：routing_key='debug' 的消息没有队列绑定，直接被丢弃了！")


# ================================================
# PART 2：Topic Exchange — 通配符模糊匹配
# ================================================
def demo_topic_exchange():
    """
    场景：IOT 设备数据路由
      设备上报格式：<国家>.<城市>.<设备类型>  例如 china.beijing.temperature

    Binding 规则（通配符匹配）：
      Queue "china_all"    ← routing_key "china.#"    (# 匹配零个或多个单词)
      Queue "temperature_all" ← routing_key "*.*.temperature" (* 精确匹配一个单词)
      Queue "beijing_only" ← routing_key "*.beijing.*"

    【Topic Exchange】routing_key 是点号分隔的单词串，支持 * 和 # 通配符
    """
    print("\n-- PART 2：Topic Exchange（通配符匹配）--")
    print("""
  【Topic Exchange】IOT 设备数据路由示意：

    routing_key: "china.beijing.temperature"
                         |
                         v
              +----------------------+
              |  Exchange "iot_data" |
              |     (topic)          |
              +------+---+---+-------+
                     |   |   |
     china.#  ------+   |   +-- *.beijing.*
                     |       (beijing_only)
     *.*.temperature -+
    (temperature_all)

  通配符规则：
    *   → 精确匹配 1 个单词    china.* 匹配 china.beijing，不匹配 china.beijing.haidian
    #   → 匹配 0 个或多个单词  china.# 匹配 china.beijing、china.beijing.haidian、china
""")

    conn, ch = get_channel()
    EXCHANGE = "demo6_iot_topic"

    ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    # 声明 3 个队列，用不同通配符绑定
    q_china = ch.queue_declare(queue="demo6_china_all", durable=True).method.queue
    q_temp = ch.queue_declare(queue="demo6_temperature_all", durable=True).method.queue
    q_beijing = ch.queue_declare(queue="demo6_beijing_only", durable=True).method.queue

    ch.queue_bind(exchange=EXCHANGE, queue=q_china, routing_key="china.#")
    ch.queue_bind(exchange=EXCHANGE, queue=q_temp, routing_key="*.*.temperature")
    ch.queue_bind(exchange=EXCHANGE, queue=q_beijing, routing_key="*.beijing.*")

    # 发送几条设备数据，观察路由结果
    events = [
        ("china.beijing.temperature", "25°C"),
        ("china.shanghai.humidity", "60%"),
        ("usa.newyork.temperature", "18°C"),
        ("china.beijing.pm25", "AQI 45"),
    ]
    for routing_key, value in events:
        ch.basic_publish(
            exchange=EXCHANGE,
            routing_key=routing_key,
            body=f"{routing_key} = {value}",
            properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE), #pika.spec.PERSISTENT_DELIVERY_MODE = 2，持久化消息
        )

    def drain_one(queue_name, label): #drain_one 函数用于从指定队列中获取一条消息并打印
        method, _, body = ch.basic_get(queue=queue_name, auto_ack=True)
        if method:
            logger.info(f"  [{label}] {body.decode()}")
        else:
            logger.info(f"  [{label}] (无消息)")

    # 消费 china_all → 应收到 3 条（所有 china.* 开头的）
    print("\n  [china_all 队列] routing_key='china.#'")
    for _ in range(4):
        drain_one(q_china, "china_all")

    # 消费 temperature_all → 应收到 2 条（*.beijing.temperature 和 *.newyork.temperature）
    print("\n  [temperature_all 队列] routing_key='*.*.temperature'")
    for _ in range(3):
        drain_one(q_temp, "temperature_all")

    # 消费 beijing_only → 应收到 2 条（*.beijing.temperature 和 *.beijing.pm25）
    print("\n  [beijing_only 队列] routing_key='*.beijing.*'")
    for _ in range(3):
        drain_one(q_beijing, "beijing_only")

    conn.close() # 关闭连接
    print("""
  > 一条消息 "china.beijing.temperature" 同时投递到了 3 个队列！
  > Topic Exchange 的核心价值：一条消息可被多个消费者按规则订阅。""")


# ================================================
# PART 3：Fanout Exchange — 广播到所有绑定队列
# ================================================
def demo_fanout_exchange():
    """
    场景：系统公告广播
      管理员发一条公告，所有微服务实例都要收到。

    【Fanout Exchange】忽略 routing_key，消息广播到所有绑定的 Queue
    典型用途：配置更新通知、缓存失效广播
    """
    print("\n-- PART 3：Fanout Exchange（广播）--")
    print("""
  【Fanout Exchange】广播示意（routing_key 被忽略）：

                          +--------------+
                     +--->|  service_a    | (订单服务)
                     |    +--------------+
  Producer --> Exchange |
  (公告)     "fanout"  |    +--------------+
                     +--->|  service_b    | (库存服务)
                     |    +--------------+
                     |    +--------------+
                     +--->|  service_c    | (通知服务)
                          +--------------+
""")

    conn, ch = get_channel()
    EXCHANGE = "demo6_broadcast_fanout"

    # 【exchange_type='fanout'】无需 routing_key，所有绑定队列都收到
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="fanout", durable=True)

    # 声明 3 个队列（模拟 3 个微服务），全部绑定到同一个 fanout exchange
    services = ["订单服务", "库存服务", "通知服务"]
    queues = {}
    for svc in services:
        q = ch.queue_declare(queue=f"demo6_{svc}", durable=True).method.queue
        # 【queue_bind 不传 routing_key】fanout 模式 routing_key 无效
        ch.queue_bind(exchange=EXCHANGE, queue=q)
        queues[svc] = q

    # 发一条公告
    announcement = "【系统公告】今晚 02:00 全量升级，届时服务暂停 30 分钟"
    ch.basic_publish(
        exchange=EXCHANGE,
        routing_key="",  # fanout 模式 routing_key 被忽略，写什么都一样
        body=announcement,
        properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE),
    )
    logger.info(f"  [Producer] 广播公告 → 3 个服务都应收到")

    # 验证每个服务都收到了
    for svc, q in queues.items():
        method, _, body = ch.basic_get(queue=q, auto_ack=True) 
        #print(method, body) 
        #eg: method=Basic.GetOk, body=b'【系统公告】今晚 02:00 全量升级，届时服务暂停 30 分钟'
        if method:
            logger.info(f"  [{svc}] 收到：{body.decode()}")
        else:
            logger.warning(f"  [{svc}] 未收到！（不该发生）")

    conn.close()


# ================================================
# PART 4：对比总结 — 三种 Exchange 选型
# ================================================
def demo_summary():
    """运行结束后打印对比表格"""
    print("\n-- 三种 Exchange 类型对比 --")
    print("""
+----------+----------------------+--------------------------+------------------+
| Exchange | 匹配方式              | 一条消息去几个队列         | 典型场景           |
+----------┼----------------------┼--------------------------┼------------------+
| direct   | routing_key 精确匹配  | 1个（同一key可绑多个队列） | 任务分发/日志路由  |
| topic    | 通配符 * 和 # 匹配    | 可多个（按订阅规则）       | IOT设备/消息订阅   |
| fanout   | 忽略 routing_key     | 全部绑定队列               | 公告广播/缓存失效  |
| headers  | 按消息 headers 匹配   | 按 headers 规则           | 复杂条件路由(少用) |
+----------+----------------------+--------------------------+------------------+

Celery 默认使用 Direct Exchange：
  每个 Task 对应一个 Queue，routing_key = 队列名 = 任务名
  Producer 发任务 → Exchange 按 routing_key 精确投递到对应 Queue → Worker 消费
""")


# ================================================
# Main
# ================================================
if __name__ == "__main__":
    print("=" * 60)
    print("RabbitMQ Exchange 类型实战：direct / topic / fanout") 
    print("=" * 60)

    try:
        demo_direct_exchange()
        time.sleep(0.3)

        demo_topic_exchange()
        time.sleep(0.3)

        demo_fanout_exchange()
        time.sleep(0.3)

        demo_summary()
        print("\n[OK] demo6 完成！")
    except pika.exceptions.AMQPConnectionError:
        print("\n[!] 无法连接 RabbitMQ，请先启动：")
        print("  docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management")
    except Exception as e:
        print(f"\n[!] 错误：{e}")