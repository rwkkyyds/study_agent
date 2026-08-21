"""AI 面试官系统请求与响应模型。"""

from pydantic import BaseModel, Field


class InterviewQuestionRequest(BaseModel):
    """生成面试题的请求。"""

    resume_text: str | None = Field(default=None, min_length=20, description="候选人简历文本")
    resume_profile_id: int | None = Field(default=None, gt=0, description="已解析候选人画像 ID")
    job_title: str = Field(min_length=2, description="目标岗位")
    difficulty: str = Field(default="mid", pattern="^(junior|mid|senior)$", description="难度")
    question_count: int = Field(default=5, ge=3, le=8, description="题目数量")


class InterviewQuestion(BaseModel):
    """单道面试题。"""

    id: str
    question_type: str
    question: str
    expected_points: list[str]
    source: str


class InterviewSessionResponse(BaseModel):
    """面试题生成响应。"""

    session_id: str
    job_title: str
    difficulty: str
    candidate_summary: str
    questions: list[InterviewQuestion]
    workflow_trace: list[str] = Field(default_factory=list)


class InterviewAnswer(BaseModel):
    """候选人对单道题的回答。"""

    question_id: str
    answer: str = Field(min_length=1)


class AnswerSubmissionRequest(BaseModel):
    """提交回答请求。"""

    session_id: str = Field(min_length=1)
    job_title: str = Field(min_length=2)
    answers: list[InterviewAnswer] = Field(min_length=1)


class InterviewFollowUpRequest(BaseModel):
    """生成追问请求。"""

    session_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class InterviewFollowUpResponse(BaseModel):
    """追问响应。"""

    session_id: str
    question_id: str
    follow_up_questions: list[str]
    reason: str
    workflow_trace: list[str] = Field(default_factory=list)


class ScoreDimension(BaseModel):
    """评分维度。"""

    name: str
    score: int = Field(ge=0, le=100)
    comment: str


class InterviewReportResponse(BaseModel):
    """面试评分报告。"""

    session_id: str
    overall_score: int = Field(ge=0, le=100)
    level: str
    dimensions: list[ScoreDimension]
    strengths: list[str]
    risks: list[str]
    follow_up_questions: list[str]
    learning_suggestions: list[str]
    workflow_trace: list[str] = Field(default_factory=list)
