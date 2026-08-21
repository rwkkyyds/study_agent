"""岗位题库检索请求与响应模型。"""

from pydantic import BaseModel, Field

class QuestionBankSearchRequest(BaseModel):
    """题库检索请求。"""

    job_title: str = Field(min_length=2, description="目标岗位")
    resume_text: str | None = Field(default=None, description="候选人简历或画像文本")
    difficulty: str = Field(default="mid", pattern="^(junior|mid|senior)$", description="题目难度")
    top_k: int = Field(default=5, ge=1, le=10, description="返回题目数量")


class QuestionBankItemResponse(BaseModel):
    """题库条目响应。"""

    id: str
    skill: str
    difficulty: str
    question_type: str
    question: str
    expected_points: list[str]
    keywords: list[str]
    source: str
    score: int


class QuestionBankSearchResponse(BaseModel):
    """题库检索响应。"""

    query_keywords: list[str]
    items: list[QuestionBankItemResponse]