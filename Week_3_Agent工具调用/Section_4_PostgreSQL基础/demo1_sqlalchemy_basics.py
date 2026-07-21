"""
Demo1: SQLAlchemy ORM 基础
功能：定义 Model → 创建表 → CRUD 操作 → 事务 → 索引
核心：理解 SQLAlchemy 的 Model/Session/Engine 三层架构
依赖：sqlalchemy（已安装）
注意：使用 SQLite 零配置运行，生产环境换 PostgreSQL 只改连接字符串
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from datetime import datetime
from sqlalchemy import create_engine, String, Integer, DateTime, Boolean, Index, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session


# ========== 1. 定义 Model（模型） ==========
# Model 是 Python 类，对应数据库的一张表
# 每个字段用 mapped_column 定义，对应表的一列
#DeclarativeBase 是所有 Model 的基类，提供元数据和映射功能
class Base(DeclarativeBase):
    """所有 Model 的基类"""
    pass


class User(Base):
    """用户表"""
    __tablename__ = "users"  # 表名

    # 主键（自增）
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 用户名（唯一索引，不能为空）
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # 邮箱（唯一索引）
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # 密码哈希（生产环境不要存明文密码）
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # 是否激活
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 创建时间（默认当前时间）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 更新时间（每次更新自动刷新）
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # 定义索引（加速查询）
    __table_args__ = ( #__table_args__ 定义表级参数，如索引、约束等
        Index("idx_user_email", "email"),           # 单字段索引   Index 的第一个参数是索引名称，后面是字段列表
        Index("idx_user_name_email", "name", "email"),  # 复合索引
    )

    def __repr__(self): #__repr__ 定义对象的字符串表示，方便调试和日志输出
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"


# ========== 2. 创建 Engine 和表 ==========
# Engine 是数据库连接池，管理所有实际连接
# create_all() 根据 Model 定义创建表（如果不存在）

def create_db():
    """创建数据库和表"""
    # SQLite 连接（文件数据库，零配置）
    # 生产环境换 PostgreSQL：
    #   engine = create_engine("postgresql+psycopg2://user:pass@localhost:5432/dbname")
    engine = create_engine("sqlite:///demo.db", echo=False)

    # 创建所有表
    Base.metadata.create_all(engine)
    print("[OK] 数据库表创建完成")
    return engine


# ========== 3. CRUD 操作 ==========
def crud_demo(engine):
    """增删改查演示"""
    print(f"\n{'=' * 60}")
    print("【CRUD 操作】")
    print("=" * 60)

    # Session 是数据库会话，跟踪所有变更
    # 使用 with 确保会话自动关闭
    with Session(engine) as session:
        # ---- Create（创建） ----
        print("\n--- Create（插入数据） ---")
        user1 = User(name="张三", email="zhangsan@example.com", password_hash="hashed_abc123")
        user2 = User(name="李四", email="lisi@example.com", password_hash="hashed_def456")
        user3 = User(name="王五", email="wangwu@example.com", password_hash="hashed_ghi789")

        session.add(user1)       # 添加单条
        session.add_all([user2, user3])  # 批量添加
        session.commit()         # 提交事务（写入数据库）

        print(f"  插入: {user1}")
        print(f"  插入: {user2}")
        print(f"  插入: {user3}")

        # ---- Read（查询） ----
        print("\n--- Read（查询数据） ---")

        # 查询所有用户
        all_users = session.query(User).all()
        print(f"  所有用户: {all_users}")

        # 条件查询（按 name）
        user = session.query(User).filter(User.name == "张三").first()
        print(f"  按 name 查询: {user}")

        # 条件查询（按 email）
        user = session.query(User).filter(User.email == "lisi@example.com").first()
        print(f"  按 email 查询: {user}")

        # 计数
        count = session.query(User).count()
        print(f"  用户总数: {count}")

        # ---- Update（更新） ----
        print("\n--- Update（更新数据） ---")
        user = session.query(User).filter(User.name == "张三").first()
        if user:
            user.email = "zhangsan_new@example.com"
            user.is_active = False
            session.commit()
            print(f"  更新后: {user}")

        # ---- Delete（删除） ----
        print("\n--- Delete（删除数据） ---")
        user = session.query(User).filter(User.name == "王五").first()
        if user:
            session.delete(user)
            session.commit()
            print(f"  已删除: 王五")

        # 验证删除
        remaining = session.query(User).all()
        print(f"  剩余用户: {remaining}")


# ========== 4. 事务演示 ==========
def transaction_demo(engine):
    """事务机制演示"""
    print(f"\n{'=' * 60}")
    print("【事务演示】")
    print("=" * 60)

    # 事务成功的情况
    print("\n--- 事务成功 ---")
    with Session(engine) as session:
        user = User(name="赵六", email="zhaoliu@example.com", password_hash="hashed_xyz")
        session.add(user)
        session.commit()  # COMMIT：写入数据库
        print(f"  事务提交: {user}")

    # 事务回滚的情况
    print("\n--- 事务回滚 ---")
    with Session(engine) as session:
        user = User(name="钱七", email="qianqi@example.com", password_hash="hashed_abc")
        session.add(user)
        session.rollback()  # ROLLBACK：撤销所有变更
        print("  事务回滚: 钱七的插入被撤销")

    # 验证回滚
    with Session(engine) as session:
        count = session.query(User).filter(User.name == "钱七").count() 
        print(f"  钱七是否不存在: {count == 0}（应为 True）")


# ========== 5. 聚合查询 ==========
def aggregation_demo(engine):
    """聚合函数演示"""
    print(f"\n{'=' * 60}")
    print("【聚合查询】")
    print("=" * 60)

    with Session(engine) as session:
        # 计数
        count = session.query(func.count(User.id)).scalar() 
        # scalar() 获取单个值（计数结果），如果没有结果返回 None
        print(f"  用户总数: {count}")

        # 按 is_active 分组统计
        results = (
            session.query(User.is_active, func.count(User.id))
            .group_by(User.is_active)
            .all()
        )
        for is_active, cnt in results:
            status = "激活" if is_active else "未激活"
            print(f"  {status}: {cnt} 人")


# ========== 6. 展示 Model 设计要点 ==========
def show_model_design():
    """展示数据模型设计要点"""
    print("=" * 60)
    print("【数据模型设计要点】")
    print("=" * 60)
    print("""
    1. 主键：自增 id（Integer）或 UUID（String）
    2. 时间字段：created_at + updated_at（自动维护）
    3. 索引：
       - 单字段索引：加速单条件查询
       - 复合索引：加速多条件查询（最左前缀原则）
       - 唯一索引：保证数据唯一性
    4. 约束：
       - nullable=False：不允许为空
       - unique=True：唯一约束
       - default：默认值
    5. 密码：存哈希值，不存明文（用 bcrypt/passlib）

    PostgreSQL vs SQLite：
    - SQLite：开发/测试用，零配置，单文件
    - PostgreSQL：生产用，支持并发、JSON、向量扩展(pgvector)
    - 连接字符串只差一行：
      SQLite:      sqlite:///demo.db
      PostgreSQL:  postgresql+psycopg2://user:pass@host:5432/dbname
    """)


# ========== 主函数 ==========
if __name__ == "__main__":
    try:
        show_model_design()

        engine = create_db()
        crud_demo(engine)
        transaction_demo(engine)
        aggregation_demo(engine)

        print(f"\n{'=' * 60}")
        print("[OK] SQLAlchemy ORM 基础 Demo 完成！")
        print("核心收获：")
        print("  1. Model 定义表结构（字段类型、索引、约束）")
        print("  2. Session 管理会话（add/commit/rollback）")
        print("  3. CRUD：query/filter/add/delete/commit")
        print("  4. 事务：with Session 自动管理，commit 提交，rollback 回滚")
        print("  5. SQLite 开发用，PostgreSQL 生产用，只改连接字符串")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
