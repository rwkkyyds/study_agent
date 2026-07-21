"""
demo5_rabbitmq_producer_consumer.py — RabbitMQ 原生 Producer / Consumer

学习目标：
1. 用 pika 库直接操作 RabbitMQ，不经过 Celery 封装
2. 理解消息流转：Producer → Exchange → Queue → Consumer
3. 掌握消息持久化（delivery_mode=2）和手动 ACK 机制
4. 理解 Celery 底层到底干了什么

运行前先启动 RabbitMQ：
  终端1: docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
         （首次需等 10s 左右 RabbitMQ 完全就绪）

  终端2: python demo5_rabbitmq_producer_consumer.py

安装依赖：pip install pika
"""

import time
import logging
import threading

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

import pika #pika 是 Python 的 RabbitMQ 客户端库，支持 AMQP 协议

# ----------------------------------------------
# RabbitMQ 连接配置
# ----------------------------------------------
# 【5672】AMQP 协议端口（程序用）
# 【15672】管理界面端口（浏览器 http://localhost:15672  账号 guest/guest）
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
QUEUE_NAME = "demo5_hello_queue"


def get_connection():
    """创建 RabbitMQ 连接"""
    # 【ConnectionParameters】连接参数：主机、端口、心跳
    # 【heartbeat=0】禁用心跳，长时间空闲也不会断开（学习用，生产不要设0）
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        heartbeat=0,
    )
    # 【BlockingConnection】同步连接，适合脚本/简单场景
    return pika.BlockingConnection(params)


# ================================================
# PART 1：最简 Producer — 发送消息
# ================================================
def demo_basic_producer():
    """Producer：向队列发送一条消息"""
    print("\n-- PART 1：Producer 发送消息 --")

    connection = get_connection()
    # 【channel】一个 TCP 连接可开多个 channel（虚拟连接），减少连接开销
    channel = connection.channel()

    # 【queue_declare】声明队列：如果队列不存在则创建
    #   durable=True → 队列持久化（RabbitMQ 重启后队列还在）
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    # 【basic_publish】发送消息到默认 Exchange（exchange=''）
    #   routing_key=QUEUE_NAME → 默认 Exchange 模式下 routing_key 就是队列名
    #   delivery_mode=2 → 消息持久化到磁盘（pika.spec.PERSISTENT_DELIVERY_MODE）
    channel.basic_publish(
        exchange="",                          # 默认 Exchange（direct 类型）
        routing_key=QUEUE_NAME,               # 路由到这个队列
        body=f"[{time.strftime('%H:%M:%S')}] Hello RabbitMQ！这是一条消息",
        properties=pika.BasicProperties(
            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,  # 消息持久化
        ),
    )
    logger.info(f"  [Producer] 消息已发送 → Queue: {QUEUE_NAME}")

    connection.close()
    return "OK"


# ================================================
# PART 2：最简 Consumer — 接收消息
# ================================================
def demo_basic_consumer():
    """Consumer：从队列拉取一条消息（.get() 方式）"""
    print("\n-- PART 2：Consumer 拉取消息（basic_get）--")

    connection = get_connection()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    # 【basic_get】主动拉取一条消息（pull 模式）
    #   auto_ack=True → 自动确认（消息取出就删，不验证是否处理成功）
    method_frame, properties, body = channel.basic_get(
        queue=QUEUE_NAME,
        auto_ack=True,
    )

    if method_frame:
        logger.info(f"  [Consumer] 收到消息：{body.decode('utf-8')}")
        print(f"  delivery_tag: {method_frame.delivery_tag}  # 消息编号，ACK/NACK 用")
    else:
        logger.info("  [Consumer] 队列为空，无消息")

    connection.close()


# ================================================
# PART 3：消息持久化验证 — RabbitMQ 重启后消息还在吗？
# ================================================
def demo_persistence():
    """
    发送持久化消息后，提示用户重启 RabbitMQ，再消费验证消息没丢。

    对比：
      delivery_mode=1（非持久化）→ RabbitMQ 重启后消息丢失
      delivery_mode=2（持久化）  → RabbitMQ 重启后消息还在
    """
    print("\n-- PART 3：消息持久化验证 --")

    # Step 1：发送一条持久化消息
    connection = get_connection()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    message = f"[PERSISTENT] 这条消息不会因为 RabbitMQ 重启而丢失"
    channel.basic_publish(
        exchange="", #exchange 是 AMQP 交换机，默认 Exchange 是 direct 类型，直接路由到队列
        routing_key=QUEUE_NAME,
        body=message,
        properties=pika.BasicProperties(    #properties 是 AMQP 消息属性
            delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE,
        ),
    )
    logger.info(f"  [Producer] 持久化消息已发送")
    connection.close()

    # Step 2：立即消费一条非持久化消息作为对比
    connection = get_connection()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_publish(
        exchange="", #exchange 是 AMQP 交换机，默认 Exchange 是 direct 类型，直接路由到队列
        routing_key=QUEUE_NAME,
        body=f"[NON-PERSISTENT] 这条消息重启后会丢失",
        properties=pika.BasicProperties(
            delivery_mode=1,  # 非持久化
        ),
    )
    logger.info(f"  [Producer] 非持久化消息已发送（用于对比）")
    connection.close()

    print("""
  现在：
    - 队列中有 2 条消息：1 条持久化 + 1 条非持久化
    - 请手动重启 RabbitMQ：
      docker restart rabbitmq
      （等待约 10s RabbitMQ 完全就绪）

    - 重启后再次运行本脚本，看看哪条消息还在？
      python demo5_rabbitmq_producer_consumer.py
""")


# ================================================
# PART 4：Push 模式 Consumer + 手动 ACK
# ================================================
def demo_push_consumer_with_ack():
    """
    Push 模式：RabbitMQ 主动推送消息给 Consumer（更常用）
    手动 ACK：Consumer 处理完才确认，处理失败消息不会丢

    【auto_ack=False】必须手动 basic_ack，否则消息一直 Unacked
    【basic_qos(prefetch_count=1)】每次只推送 1 条，处理完再发下一条（公平分发）
    """
    print("\n-- PART 4：Push 模式 Consumer + 手动 ACK --")

    def on_message(ch, method, properties, body): #properties 是 AMQP 消息属性，包含 headers、delivery_mode 等
        """
        消息回调：RabbitMQ 推送消息时自动调用
        【ch】channel 对象
        【method】包含 delivery_tag（消息唯一编号）、exchange、routing_key
        【properties】消息属性（headers、delivery_mode 等）
        【body】消息体（bytes）
        """
        msg = body.decode("utf-8")
        logger.info(f"  [Consumer] 收到：{msg}")

        # 模拟处理：偶数消息"处理失败"，奇数消息成功
        tag = method.delivery_tag % 10  # 取个位数模拟业务逻辑  # print(method.delivery_tag)  # 1,2,3,4,5...
        if tag % 2 == 0:
            # 【basic_nack】不确认，requeue=True 让消息重回队列
            logger.warning(f"  处理失败！消息 #{method.delivery_tag} 重回队列")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  
        else:
            # 【basic_ack】确认消息已处理，RabbitMQ 从队列中删除
            logger.info(f"  处理成功！消息 #{method.delivery_tag} 已确认")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    connection = get_connection()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    # 【prefetch_count=1】QoS 限流：同时只处理 1 条消息（防止某个 Consumer 被压垮）
    channel.basic_qos(prefetch_count=1)

    # 【basic_consume】注册消费者（push 模式）
    #   on_message_callback → 收到消息时回调这个函数
    #   auto_ack=False      → 手动确认
    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=on_message,
        auto_ack=False,
    )

    logger.info("  [Consumer] 开始监听队列... (10s 后自动停止)")
    # 在独立线程中启动消费循环，主线程等 10 秒后停止
    def consume():
        try:
            # 【start_consuming()】阻塞循环，不断接收消息
            channel.start_consuming()
        except Exception:
            pass  # 主线程 stop_consuming 会触发异常，忽略

    t = threading.Thread(target=consume, daemon=True)
    t.start()
    time.sleep(10)
    channel.stop_consuming()
    connection.close()
    logger.info("  [Consumer] 监听停止")


# ================================================
# Main — 串联演示
# ================================================
if __name__ == "__main__":
    print("=" * 60)
    print("RabbitMQ 原生 Producer / Consumer 演示")
    print("=" * 60)
    print("""
架构图（没有 Celery 封装，直接操作 RabbitMQ）：

  Producer                         Consumer
     |                                |
     |  basic_publish()               |  basic_consume() / basic_get()
     v                                v
  +-----------------------------------------+
  |              RabbitMQ                    |
  |  +----------+    +-----------------+    |
  |  | Exchange |--->|     Queue       |    |
  |  | (默认)    |    | (消息缓冲区)      |    |
  |  +----------+    +-----------------+    |
  +-----------------------------------------+

Celery 的 .delay() 本质就是 basic_publish()！
Celery Worker 本质就是 basic_consume() 的消费者！
""")

    try:
        demo_basic_producer()
        time.sleep(0.5)

        demo_basic_consumer()
        time.sleep(0.5)

        demo_persistence()

        demo_push_consumer_with_ack()

        print("\n[OK] demo5 完成！")
    except pika.exceptions.AMQPConnectionError:
        print("\n[!] 无法连接 RabbitMQ，请先启动：")
        print("  docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management")
        print("  （首次需等约 10s RabbitMQ 完全就绪）")
    except Exception as e:
        print(f"\n[!] 错误：{e}")
