"""认证相关的 Pydantic Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """用户注册请求体。"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    role: str = Field(default="customer", pattern="^(admin|agent|customer)$", description="角色")


class LoginRequest(BaseModel):
    """用户登录请求体。"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """登录成功返回的 JWT Token。"""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """用户信息响应体。"""

    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}