"""认证相关请求与响应模型。"""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """候选人注册请求。"""

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str
    password: str


class AdminCreateUserRequest(BaseModel):
    """管理员创建用户请求。"""

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(default="candidate", pattern="^(candidate|admin)$")


class TokenResponse(BaseModel):
    """登录成功后的令牌响应。"""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """用户响应。"""

    id: int
    username: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}

