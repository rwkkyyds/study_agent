"""认证相关 Pydantic 请求/响应模型。"""

from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class TokenResponse(BaseModel):
    """登录成功返回的 JWT token。"""

    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_at: datetime.datetime = Field(..., description="令牌过期时间")


class UserCreate(BaseModel):
    """用户注册请求。"""

    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    display_name: Optional[str] = Field(None, max_length=64, description="显示名称")
    email: Optional[str] = Field(None, max_length=128, description="邮箱")
    role: str = Field("customer", description="角色：admin/agent/customer")


class UserResponse(BaseModel):
    """用户信息响应（不含密码）。"""

    id: int
    username: str
    role: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class UserProfile(BaseModel):
    """当前用户信息（含更多字段）。"""

    id: int
    username: str
    role: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    created_at: datetime.datetime

    model_config = {"from_attributes": True}