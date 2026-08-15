"""创建初始管理员账号的引导脚本。

用法（在项目根目录执行）：
    python scripts/create_admin.py
    python scripts/create_admin.py --username admin --password "强密码123" --role admin

说明：
- 第一个 admin 账号无法通过接口创建（接口本身需要 admin 权限），
  因此提供本脚本作为引导。创建后即可登录系统，
  并在「用户管理」页面用接口创建更多 agent/admin 账号。
- 已存在的用户名不会被覆盖。
"""

import argparse
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保 `app` 包可被导入（无论从哪个目录执行）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal, init_db
from app.services.auth import create_user


def main() -> None:
    parser = argparse.ArgumentParser(description="创建初始管理员/客服账号")
    parser.add_argument("--username", default="admin", help="用户名（默认 admin）")
    parser.add_argument("--password", default="admin123", help="密码（默认 admin123，建议立即修改）")
    parser.add_argument(
        "--role",
        default="admin",
        choices=["admin", "agent", "customer"],
        help="角色（默认 admin）",
    )
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        user = create_user(db, username=args.username, password=args.password, role=args.role)
        print(f"✅ 创建成功：id={user.id} username={user.username} role={user.role}")
        print("  可用该账号登录 http://localhost:3000/login")
    except Exception as exc:
        if "用户名已存在" in str(exc):
            print(f"⚠️  用户名 {args.username} 已存在，未做修改")
        else:
            print(f"❌ 创建失败：{exc}")
            raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
