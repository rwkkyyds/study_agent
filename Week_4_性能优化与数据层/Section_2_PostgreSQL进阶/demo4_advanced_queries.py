"""
demo4_advanced_queries.py - 高级查询：窗口函数 + CTE

运行：python demo4_advanced_queries.py
前置：PostgreSQL 已启动，密码 123456
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, DeclarativeBase
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime, timedelta
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql+psycopg2://postgres:123456@localhost:5432/postgres"


class Base(DeclarativeBase):
    pass


class Sale(Base):
    """销售表"""
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    salesperson = Column(String(50), nullable=False)  # 销售员
    region = Column(String(50), nullable=False)        # 区域
    product = Column(String(100), nullable=False)      # 产品
    amount = Column(Float, nullable=False)             # 金额
    sale_date = Column(DateTime, nullable=False)       # 日期


def init_data(session: Session, engine):
    """造500条随机销售数据"""
    logger.info("正在创建测试数据...")
    session.execute(text("DROP TABLE IF EXISTS sales CASCADE"))
    session.commit()
    Base.metadata.create_all(engine)  # 根据Model建表

    names = ["张三", "李四", "王五", "赵六", "钱七"]
    regions = ["华东", "华南", "华北", "西南"]
    products = ["手机", "笔记本", "耳机", "平板"]

    for _ in range(500):
        session.add(Sale(
            salesperson=random.choice(names),
            region=random.choice(regions),
            product=random.choice(products),
            amount=round(random.uniform(100, 10000), 2),
            sale_date=datetime.now() - timedelta(days=random.randint(0, 90)),
        ))
    session.commit()
    logger.info("500条数据就绪")


# ============================================================
# Part 1: GROUP BY vs 窗口函数 — 先搞清楚有什么区别
# ============================================================
def demo_groupby_vs_window(session: Session):
    """
    GROUP BY    → 多行合成一行，只看到结果，看不到明细
    窗口函数    → 每行都留着，旁边附加一列计算结果

    类比：
      GROUP BY = 全班只告诉你平均分
      窗口函数 = 每个学生的成绩单上印着"班级平均分"
    """
    logger.info("\n" + "="*60)
    logger.info("【Part 1】GROUP BY vs 窗口函数")
    logger.info("="*60)

    # --- GROUP BY：只能看到总计，看不到每笔订单 ---
    logger.info("\n--- GROUP BY：只看到总计 ---")
    result = session.execute(text("""
        SELECT
            salesperson,           -- 销售员
            SUM(amount) as total   -- SUM = 求和
        FROM sales
        GROUP BY salesperson       -- GROUP BY = 按人合并成一行
    """))
    for row in result:
        logger.info(f"  {row[0]} 总销售额: ¥{row[1]:>10.2f}")

    # --- 窗口函数：每笔订单都在，旁边多了"这个人总共多少" ---
    logger.info("\n--- 窗口函数：保留每笔明细 + 旁边附上总额 ---")
    result = session.execute(text("""
        SELECT
            salesperson,           -- 销售员
            amount,                -- 这笔订单金额
            SUM(amount) OVER (     -- OVER = 开一扇"窗"，看一组数据
                PARTITION BY salesperson  -- PARTITION BY = 按人分组
            ) as person_total      -- 每行都显示这个人的总销售额
        FROM sales
        ORDER BY salesperson, amount DESC
        LIMIT 10
    """))
    for row in result:
        logger.info(f"  {row[0]} | 这笔 ¥{row[1]:>8.2f} | 他总共 ¥{row[2]:>10.2f}")


# ============================================================
# Part 2: ROW_NUMBER — 给每行编号
# ============================================================
def demo_row_number(session: Session):
    """
    ROW_NUMBER() = 给行编号，从1开始，不重复

    语法：
      ROW_NUMBER() OVER ( PARTITION BY 分组列  ORDER BY 排序列 )

    PARTITION BY = 按谁分组（省略 = 全表一起排）
    ORDER BY    = 按什么排序（谁排第一谁编号1）

    类比：每个班级按成绩给学生编号 1,2,3...
    """
    logger.info("\n" + "="*60)
    logger.info("【Part 2】ROW_NUMBER — 给每行编号")
    logger.info("="*60)

    result = session.execute(text("""
        SELECT
            salesperson,
            product,
            amount,
            ROW_NUMBER() OVER (            -- 编号函数
                PARTITION BY salesperson   -- 每人单独编号
                ORDER BY amount DESC       -- 金额大的排第1
            ) as ranking                   -- 列别名：这人的第几名
        FROM sales
        ORDER BY salesperson, ranking
    """))
    for row in result:
        # row[0]=销售员 row[1]=产品 row[2]=金额 row[3]=排名
        logger.info(f"  {row[0]} | 第{row[3]}名 | {row[1]} | ¥{row[2]:>8.2f}")


# ============================================================
# Part 3: RANK vs DENSE_RANK — 三种排名的区别
# ============================================================
def demo_rank_types(session: Session):
    """
    三种编号的区别（面试常考）：

      ROW_NUMBER → 1,2,3,4  （永不重复）
      RANK       → 1,1,3,4  （值相同→并列→跳号）
      DENSE_RANK → 1,1,2,3  （值相同→并列→不跳号）

    例：分数 100,100,80
      ROW_NUMBER → 1,2,3
      RANK       → 1,1,3   ← 第2名被跳过了
      DENSE_RANK → 1,1,2   ← 不跳号
    """
    logger.info("\n" + "="*60)
    logger.info("【Part 3】三种排名：ROW_NUMBER / RANK / DENSE_RANK")
    logger.info("="*60)

    logger.info("\n--- RANK：按区域排名（并列就跳号）---")
    result = session.execute(text("""
        SELECT
            region,
            salesperson,
            amount,
            RANK() OVER (                   -- RANK：有并列会跳号
                PARTITION BY region         -- 每个区域内部排名
                ORDER BY amount DESC        -- 金额高排前面
            ) as rk
        FROM sales
        ORDER BY region, rk
        LIMIT 12
    """))
    for row in result:
        logger.info(f"  {row[0]} | 第{row[3]}名 | {row[1]} | ¥{row[2]:>8.2f}")


# ============================================================
# Part 4: SUM OVER — 累计求和
# ============================================================
def demo_sum_over(session: Session):
    """
    累计求和 = 从第一行加到当前行

    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    rows between unbounded preceding and current row = 从窗口最开头加到当前行
      UNBOUNDED PRECEDING = 从窗口最开头
      CURRENT ROW        = 到当前行

    场景：看销售额随时间的增长趋势
    效果：每行数字越来越大（因为一直在加）
    """
    logger.info("\n" + "="*60)
    logger.info("【Part 4】累计求和 — 从头加到当前行")
    logger.info("="*60)

    logger.info("\n--- 张三的累计销售额（每天越加越多）---")
    result = session.execute(text("""
        SELECT
            salesperson,
            sale_date,
            amount,
            SUM(amount) OVER (
                PARTITION BY salesperson     -- 只算张三自己的
                ORDER BY sale_date           -- 按日期从小到大
                ROWS BETWEEN                 -- 窗口范围：
                    UNBOUNDED PRECEDING       -- 从最开头
                    AND CURRENT ROW           -- 到当前行
            ) as running_total              -- 累计金额
        FROM sales
        WHERE salesperson = '张三'
        ORDER BY sale_date
        LIMIT 10
    """))
    for row in result:
        date_str = str(row[1])[:10]
        logger.info(f"  {date_str} | 这笔 ¥{row[2]:>8.2f} | 累计 ¥{row[3]:>10.2f}")


# ============================================================
# Part 5: LAG — 取前一行的值
# ============================================================
def demo_lag(session: Session):
    """
    LAG(列名, 往前看几行) = 取前一行的值

    LAG(amount, 1) → 上一行的amount
    第一行没有"上一行" → 返回 NULL

    场景：环比增长（本期 vs 上期）
          公式：(本期 - 上期) / 上期 × 100%
    """
    logger.info("\n" + "="*60)
    logger.info("【Part 5】LAG — 取前一行的值（环比）")
    logger.info("="*60)

    logger.info("\n--- 张三每笔订单 vs 上一笔：涨了还是跌了 ---")
    result = session.execute(text("""
        WITH ordered AS (                     -- CTE：先把订单排好序
            SELECT
                amount,
                ROW_NUMBER() OVER (           -- 按日期降序编号
                    ORDER BY sale_date DESC    -- 最新的=1
                ) as rn
            FROM sales
            WHERE salesperson = '张三'
        )
        SELECT
            amount as "本次",
            LAG(amount, 1) OVER (            -- LAG=取前一行 1=往前1步
                ORDER BY rn DESC
            ) as "上次",
            ROUND((                           -- ROUND=保留2位小数
                (amount - LAG(amount, 1) OVER (ORDER BY rn DESC))
                * 100.0 /
                LAG(amount, 1) OVER (ORDER BY rn DESC)
            )::numeric, 2) as "变化%"
        FROM ordered
        WHERE rn <= 5
        ORDER BY rn DESC
    """))
    for row in result:
        prev = f"¥{row[1]:>8.2f}" if row[1] else "     N/A"
        change = f"{row[2]:>6.2f}%" if row[2] is not None else "   N/A"
        logger.info(f"  本次 ¥{row[0]:>8.2f} | 上次 {prev} | 变化 {change}")


# ============================================================
# Part 6: CTE — 把复杂SQL拆成多步
# ============================================================
def demo_cte(session: Session):
    """
    CTE = WITH ... AS (...) → 给子查询起名，把复杂SQL拆成步骤

    子查询：括号套括号，从里往外读 → 反人类
    CTE：   从上往下读，先定义再使用 → 像写步骤

    语法：
        WITH 名字1 AS (
            SELECT ...          -- 第1步
        ),
        名字2 AS (
            SELECT ... FROM 名字1  -- 第2步（可以用第1步的结果）
        )
        SELECT ... FROM 名字2      -- 最后查询
    """
    logger.info("\n" + "="*60)
    logger.info("【Part 6】CTE — 把复杂查询拆成步骤")
    logger.info("="*60)

    logger.info("\n--- 三步走：找到每个区域的销售冠军 ---")
    result = session.execute(text("""
        -- 第1步：把每个人在每个区域的销售额汇总
        WITH summary AS (
            SELECT
                region,
                salesperson,
                SUM(amount) as total,     -- 总销售额
                COUNT(*) as orders        -- 订单数
            FROM sales
            GROUP BY region, salesperson  -- 按区域+人分组
        ),
        -- 第2步：每个区域内部排名
        ranking AS (
            SELECT
                *,
                RANK() OVER (
                    PARTITION BY region        -- 按区域分组
                    ORDER BY total DESC        -- 总额高的排前面
                ) as rk
            FROM summary
        )
        -- 第3步：取每个区域的第一名
        SELECT region, salesperson, total, orders
        FROM ranking
        WHERE rk = 1
        ORDER BY total DESC
    """))
    for row in result:
        logger.info(f"  {row[0]} 冠军 → {row[1]} | ¥{row[2]:>10.2f} | {row[3]}笔")


# ============================================================
# Part 7: Top-N — 每个分组取前N条（面试必考）
# ============================================================
def demo_top_n(session: Session):
    """
    Top-N = 每个分组取前N条

    面试题："每个部门工资最高的3个人"

    万能公式（背下来）：
        WITH ranked AS (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY 分组列 ORDER BY 排序列 DESC
            ) as rn
            FROM 表
        )
        SELECT * FROM ranked WHERE rn <= N;
    """
    logger.info("\n" + "="*60)
    logger.info("【Part 7】Top-N：每个区域销售额前3的销售员")
    logger.info("="*60)

    result = session.execute(text("""
        WITH ranked AS (
            SELECT
                region,
                salesperson,
                SUM(amount) as total,
                ROW_NUMBER() OVER (         -- 按区域编号
                    PARTITION BY region     -- 每个区域内部
                    ORDER BY SUM(amount) DESC  -- 金额大的排第1
                ) as rn
            FROM sales
            GROUP BY region, salesperson
        )
        SELECT region, salesperson, total, rn
        FROM ranked
        WHERE rn <= 3                       -- 只要前3
        ORDER BY region, rn
    """))
    for row in result:
        logger.info(f"  {row[0]} | 第{row[3]}名 {row[1]} | ¥{row[2]:>10.2f}")


# ============================================================
# 主程序
# ============================================================
def main():
    engine = create_engine(DB_URL, echo=False)

    with Session(engine) as session:
        init_data(session, engine)

        demo_groupby_vs_window(session)   # Part1: GROUP BY vs 窗口函数（区别）
        demo_row_number(session)          # Part2: ROW_NUMBER 编号
        demo_rank_types(session)          # Part3: 三种排名区别
        demo_sum_over(session)            # Part4: 累计求和
        demo_lag(session)                 # Part5: LAG 取前一行的值
        demo_cte(session)                 # Part6: CTE 分步查询
        demo_top_n(session)               # Part7: Top-N 面试必考公式


if __name__ == "__main__":
    main()
