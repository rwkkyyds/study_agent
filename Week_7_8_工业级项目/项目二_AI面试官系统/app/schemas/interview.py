"""AI 面试官系统请求与响应模型。"""

from datetime import datetime

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


class FollowUpStreamTokenRequest(InterviewFollowUpRequest):
    """创建 SSE 追问访问令牌的请求。"""


class FollowUpStreamTokenResponse(BaseModel):
    """SSE 追问访问令牌响应。"""

    stream_token: str
    token_type: str = "bearer"
    expires_in: int


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


class InterviewAnswerRecord(InterviewAnswer):
    """已保存的候选人回答。"""

    created_at: datetime


class InterviewFollowUpRecord(BaseModel):
    """已保存的追问记录。"""

    question_id: str
    answer: str
    follow_up_questions: list[str]
    reason: str
    workflow_trace: list[str] = Field(default_factory=list)
    created_at: datetime


class InterviewSessionSummary(BaseModel):
    """面试会话列表项。"""

    session_id: str
    job_title: str
    difficulty: str
    status: str
    candidate_summary: str
    question_count: int
    answer_count: int
    follow_up_count: int
    overall_score: int | None = None
    level: str | None = None
    created_at: datetime
    updated_at: datetime


class InterviewSessionListResponse(BaseModel):
    """面试会话列表响应。"""

    sessions: list[InterviewSessionSummary]


class InterviewSessionDetailResponse(InterviewSessionSummary):
    """面试会话详情响应。"""

    resume_text: str
    questions: list[InterviewQuestion]
    answers: list[InterviewAnswerRecord]
    follow_ups: list[InterviewFollowUpRecord]
    report: InterviewReportResponse | None = None
