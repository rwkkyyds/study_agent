"""简历解析请求与响应模型。"""

from pydantic import BaseModel, Field


class ResumeParseRequest(BaseModel):
    """文本或 Markdown 简历解析请求。"""

    content: str = Field(min_length=20, description="简历正文")
    content_type: str = Field(default="text", pattern="^(text|markdown)$", description="简历类型")
    target_job_title: str | None = Field(default=None, min_length=2, max_length=120, description="目标岗位")
    source_name: str | None = Field(default=None, max_length=255, description="简历来源名称")


class ResumeProfileResponse(BaseModel):
    """候选人画像响应。"""

    id: int
    source_type: str
    source_name: str | None
    summary: str
    skills: list[str]
    projects: list[str]
    years_of_experience: int | None
    target_keywords: list[str]
    normalized_text: str

    model_config = {"from_attributes": True}
