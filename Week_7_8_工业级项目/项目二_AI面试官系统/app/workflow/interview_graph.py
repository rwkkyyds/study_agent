"""阶段五图式面试工作流。

当前用本地确定性节点模拟 LangGraph 的 StateGraph 思路：
state -> node -> state -> conditional node -> output。
阶段五加入本地岗位题库检索节点，模拟后续向量库/RAG 召回。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from app.schemas.interview import (
    AnswerSubmissionRequest,
    InterviewFollowUpRequest,
    InterviewFollowUpResponse,
    InterviewQuestion,
    InterviewQuestionRequest,
    InterviewReportResponse,
    InterviewSessionResponse,
    ScoreDimension,
)
from app.services.question_bank import QuestionBankRetriever
from app.services.qwen_llm import QwenInterviewLLM, build_interview_llm


@dataclass(frozen=True)
class ResumeSignal:
    """从简历文本中抽取出的弱信号。"""

    has_rag: bool
    has_agent: bool
    has_backend: bool
    has_frontend: bool
    has_deploy: bool


@dataclass(frozen=True)
class JobProfile:
    """岗位画像。"""

    title: str
    track: str
    focus_keywords: list[str]
    seniority: str


@dataclass
class InterviewGraphState:
    """图式工作流状态容器。"""

    resume_text: str = ""
    job_title: str = ""
    difficulty: str = "mid"
    question_count: int = 5
    session_id: str = ""
    resume_signals: ResumeSignal | None = None
    job_profile: JobProfile | None = None
    candidate_summary: str = ""
    retrieved_questions: list[InterviewQuestion] = field(default_factory=list)
    questions: list[InterviewQuestion] = field(default_factory=list)
    answer_text: str = ""
    dimension_scores: dict[str, int] = field(default_factory=dict)
    follow_up_questions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    learning_suggestions: list[str] = field(default_factory=list)
    workflow_trace: list[str] = field(default_factory=list)


class InterviewWorkflow:
    """AI 面试官图式工作流门面。"""

    def __init__(
        self,
        question_bank: QuestionBankRetriever | None = None,
        llm: QwenInterviewLLM | None = None,
    ) -> None:
        self.question_bank = question_bank or QuestionBankRetriever()
        self.llm = llm if llm is not None else build_interview_llm()

    def generate_questions(self, request: InterviewQuestionRequest) -> InterviewSessionResponse:
        """运行：简历解析 -> 岗位画像 -> RAG 检索 -> 题目生成。"""

        state = InterviewGraphState(
            resume_text=(request.resume_text or "").strip(),
            job_title=request.job_title,
            difficulty=request.difficulty,
            question_count=request.question_count,
        )
        self._resume_parse_node(state)
        self._job_profile_node(state)
        self._rag_retrieval_node(state)
        self._question_generation_node(state)
        return InterviewSessionResponse(
            session_id=state.session_id,
            job_title=state.job_title,
            difficulty=state.difficulty,
            candidate_summary=state.candidate_summary,
            questions=state.questions[: state.question_count],
            workflow_trace=state.workflow_trace,
        )

    def generate_follow_up(self, request: InterviewFollowUpRequest, job_title: str) -> InterviewFollowUpResponse:
        """运行：候选人回答 -> 追问生成。"""

        state = InterviewGraphState(job_title=job_title, answer_text=request.answer.strip())
        self._answer_analysis_node(state)
        self._follow_up_node(state, base_question_id=request.question_id)
        reason = "根据回答中的技术细节、结构完整度和风险意识生成追问。"
        return InterviewFollowUpResponse(
            session_id=request.session_id,
            question_id=request.question_id,
            follow_up_questions=state.follow_up_questions,
            reason=reason,
            workflow_trace=state.workflow_trace,
        )

    def evaluate_answers(self, request: AnswerSubmissionRequest) -> InterviewReportResponse:
        """运行：候选人回答 -> 评分 -> 报告生成。"""

        if not request.answers:
            raise ValueError("至少需要提交一道题的回答")

        state = InterviewGraphState(
            session_id=request.session_id,
            job_title=request.job_title,
            answer_text="\n".join(item.answer for item in request.answers),
        )
        self._answer_analysis_node(state)
        self._scoring_node(state)
        self._report_node(state)
        scores = state.dimension_scores
        overall = round(
            (scores["technical"] * 0.35)
            + (scores["structure"] * 0.25)
            + (scores["project"] * 0.25)
            + (scores["risk"] * 0.15)
        )
        return InterviewReportResponse(
            session_id=request.session_id,
            overall_score=overall,
            level=self._level(overall),
            dimensions=[
                ScoreDimension(name="技术匹配度", score=scores["technical"], comment="是否能讲清岗位核心技术栈和实现细节。"),
                ScoreDimension(name="表达结构", score=scores["structure"], comment="回答是否有层次、有原因、有取舍。"),
                ScoreDimension(name="项目理解", score=scores["project"], comment="是否能从业务闭环而不是单点 API 解释项目。"),
                ScoreDimension(name="风险意识", score=scores["risk"], comment="是否能主动说明不足、监控、降级和后续优化。"),
            ],
            strengths=state.strengths,
            risks=state.risks,
            follow_up_questions=state.follow_up_questions,
            learning_suggestions=state.learning_suggestions,
            workflow_trace=state.workflow_trace,
        )

    def _resume_parse_node(self, state: InterviewGraphState) -> None:
        if not state.resume_text:
            raise ValueError("简历内容不能为空")
        state.resume_signals = self._extract_signals(state.resume_text)
        state.session_id = self._session_id(state.resume_text, state.job_title, state.difficulty)
        state.candidate_summary = self._summarize_candidate(state.resume_signals)
        state.workflow_trace.append("resume_parse_node")

    def _job_profile_node(self, state: InterviewGraphState) -> None:
        title = state.job_title.lower()
        focus_keywords: list[str] = []
        track = "general"
        if "ai" in title or "智能" in state.job_title or "算法" in state.job_title:
            track = "ai_application"
            focus_keywords.extend(["LLM", "RAG", "Agent", "模型评估"])
        if "后端" in state.job_title or "开发" in state.job_title:
            focus_keywords.extend(["API 设计", "数据库", "缓存", "部署"])
        if "前端" in state.job_title or "全栈" in state.job_title:
            focus_keywords.extend(["交互体验", "状态管理", "接口联调"])
        if not focus_keywords:
            focus_keywords.extend(["项目理解", "工程实践", "沟通结构"])
        state.job_profile = JobProfile(
            title=state.job_title,
            track=track,
            focus_keywords=sorted(set(focus_keywords), key=focus_keywords.index),
            seniority=state.difficulty,
        )
        state.workflow_trace.append("job_profile_node")

    def _rag_retrieval_node(self, state: InterviewGraphState) -> None:
        if state.job_profile is None:
            raise ValueError("题库检索前必须先完成岗位画像")
        state.retrieved_questions = self.question_bank.retrieve_for_interview(
            job_title=state.job_title,
            resume_text=state.resume_text,
            difficulty=state.difficulty,
            top_k=3,
        )
        state.workflow_trace.append("rag_retrieval_node")

    def _question_generation_node(self, state: InterviewGraphState) -> None:
        if state.resume_signals is None or state.job_profile is None:
            raise ValueError("题目生成前必须先完成简历解析和岗位画像")
        state.questions = self._build_questions(state, state.resume_signals, state.job_profile)
        state.workflow_trace.append("question_generation_node")
        self._qwen_question_enrichment_node(state)

    def _answer_analysis_node(self, state: InterviewGraphState) -> None:
        if not state.answer_text.strip():
            raise ValueError("回答内容不能为空")
        state.dimension_scores = {
            "technical": self._score_by_keywords(state.answer_text, ["RAG", "向量", "Milvus", "Redis", "PostgreSQL", "Docker", "LangGraph"]),
            "structure": self._score_by_keywords(state.answer_text, ["首先", "其次", "最后", "流程", "原因", "权衡", "指标"]),
            "project": self._score_by_keywords(state.answer_text, ["项目", "业务", "用户", "权限", "测试", "部署", "稳定性"]),
            "risk": self._score_by_keywords(state.answer_text, ["不足", "优化", "风险", "降级", "监控", "扩展", "瓶颈"]),
        }
        state.workflow_trace.append("answer_analysis_node")

    def _follow_up_node(self, state: InterviewGraphState, base_question_id: str | None = None) -> None:
        scores = state.dimension_scores or {}
        follow_ups = []
        if scores.get("technical", 0) < 70:
            follow_ups.append("请补充一个你亲自实现的关键技术细节，并说明为什么这样设计。")
        if scores.get("structure", 0) < 70:
            follow_ups.append("请按 背景-方案-结果-复盘 重新组织一次回答。")
        if scores.get("risk", 0) < 70:
            follow_ups.append("如果这个方案上线后出现故障，你会如何监控、降级和回滚？")
        if not follow_ups:
            follow_ups.extend([
                f"围绕 {state.job_title} 的真实面试，你认为这段经历最容易被追问哪一个瓶颈？",
                "请给出一个量化指标，证明这个项目不是只停留在 demo。",
            ])
        if base_question_id:
            follow_ups.append(f"针对 {base_question_id}，请补充你在项目中的个人贡献边界。")
        state.follow_up_questions = follow_ups[:3]
        state.workflow_trace.append("follow_up_node")
        self._qwen_follow_up_enrichment_node(state, base_question_id)

    def _scoring_node(self, state: InterviewGraphState) -> None:
        self._follow_up_node(state)
        scores = state.dimension_scores
        state.strengths = self._strengths(scores["technical"], scores["structure"], scores["project"])
        state.risks = self._risks(scores["technical"], scores["structure"], scores["risk"])
        state.workflow_trace.append("scoring_node")

    def _report_node(self, state: InterviewGraphState) -> None:
        state.learning_suggestions = [
            "准备一版 30 秒项目介绍和一版 2 分钟深挖版本。",
            "每个技术点都绑定业务原因，例如为什么要用 RAG、Redis、Docker。",
            "把项目不足说成生产化演进方向，不要只说功能还没做。",
        ]
        state.workflow_trace.append("report_node")

    @staticmethod
    def _extract_signals(resume: str) -> ResumeSignal:
        text = resume.lower()
        return ResumeSignal(
            has_rag="rag" in text or "向量" in resume or "知识库" in resume,
            has_agent="agent" in text or "langgraph" in text or "智能体" in resume,
            has_backend="fastapi" in text or "后端" in resume or "api" in text,
            has_frontend="react" in text or "next" in text or "前端" in resume,
            has_deploy="docker" in text or "部署" in resume or "compose" in text,
        )

    @staticmethod
    def _session_id(resume: str, job_title: str, difficulty: str) -> str:
        raw = f"{resume[:120]}|{job_title}|{difficulty}".encode("utf-8")
        return "iv-" + hashlib.sha1(raw).hexdigest()[:12]

    @staticmethod
    def _summarize_candidate(signals: ResumeSignal) -> str:
        strengths: list[str] = []
        if signals.has_rag:
            strengths.append("RAG/知识库")
        if signals.has_agent:
            strengths.append("Agent/LangGraph")
        if signals.has_backend:
            strengths.append("后端 API")
        if signals.has_frontend:
            strengths.append("前端交互")
        if signals.has_deploy:
            strengths.append("Docker 部署")
        if not strengths:
            return "简历暂未识别到明显 AI 工程关键词，需要通过基础题确认项目真实性。"
        return "简历中可重点追问：" + "、".join(strengths)

    @staticmethod
    def _build_questions(state: InterviewGraphState, signals: ResumeSignal, job_profile: JobProfile) -> list[InterviewQuestion]:
        focus = "、".join(job_profile.focus_keywords[:3])
        questions = [
            InterviewQuestion(
                id="q1",
                question_type="project_deep_dive",
                question=f"请用 1 分钟介绍你最能代表 {state.job_title} 能力的项目，并说明它解决了什么业务问题。",
                expected_points=["业务痛点", "核心用户", "技术架构", "个人贡献"],
                source="岗位通用项目深挖",
            ),
            InterviewQuestion(
                id="q2",
                question_type="job_profile",
                question=f"这个岗位重点关注 {focus}，请结合你的项目说明最匹配的一段经历。",
                expected_points=["岗位关键词", "项目证据", "技术取舍", "结果指标"],
                source="岗位画像节点",
            ),
        ]
        questions.extend(state.retrieved_questions)
        questions.append(InterviewQuestion(
            id="q3",
            question_type="system_design",
            question="如果面试官要求你把这个项目支撑到 10 倍用户量，你会优先改哪些模块？",
            expected_points=["瓶颈识别", "缓存/队列", "数据库索引", "异步化", "监控指标"],
            source="系统设计能力",
        ))
        if signals.has_rag:
            questions.append(InterviewQuestion(
                id="q4",
                question_type="rag",
                question="请解释你的 RAG 链路：文档如何入库、如何检索、如何降低幻觉？",
                expected_points=["Chunking", "Embedding", "Vector Search", "top_k", "sources", "评估"],
                source="简历 RAG 信号",
            ))
        if signals.has_agent:
            questions.append(InterviewQuestion(
                id="q5",
                question_type="agent",
                question="你的 Agent 工作流如何做条件路由、工具调用失败和人工介入？",
                expected_points=["StateGraph", "条件边", "工具抽象", "重试降级", "HITL"],
                source="简历 Agent 信号",
            ))
        if signals.has_deploy:
            questions.append(InterviewQuestion(
                id="q6",
                question_type="deployment",
                question="你如何用 Docker Compose 组织前端、后端、数据库、缓存和向量库？",
                expected_points=["服务拆分", "环境变量", "健康检查", "数据卷", "网络"],
                source="简历部署信号",
            ))
        questions.append(InterviewQuestion(
            id="q7",
            question_type="self_review",
            question="如果让你现在继续优化这个项目，你认为最值得补的三件事是什么？",
            expected_points=["生产化不足", "优先级", "业务价值", "落地方案"],
            source="成长潜力评估",
        ))
        return questions

    @staticmethod
    def _score_by_keywords(text: str, keywords: list[str]) -> int:
        hit = sum(1 for keyword in keywords if keyword.lower() in text.lower())
        return min(100, 45 + hit * 10)

    @staticmethod
    def _level(score: int) -> str:
        if score >= 85:
            return "强通过"
        if score >= 70:
            return "通过"
        if score >= 60:
            return "待定"
        return "风险较高"

    def _qwen_question_enrichment_node(self, state: InterviewGraphState) -> None:
        if self.llm is None:
            return
        try:
            qwen_questions = self.llm.generate_questions(
                resume_text=state.resume_text,
                job_title=state.job_title,
                difficulty=state.difficulty,
                question_count=state.question_count,
                current_questions=state.questions,
            )
        except RuntimeError:
            state.workflow_trace.append("qwen_question_enrichment_skipped")
            return

        if not qwen_questions:
            return
        state.questions = [*state.questions[:2], *qwen_questions, *state.questions[2:]]
        state.workflow_trace.append("qwen_question_enrichment_node")

    def _qwen_follow_up_enrichment_node(self, state: InterviewGraphState, base_question_id: str | None) -> None:
        if self.llm is None:
            return
        try:
            follow_ups = self.llm.generate_follow_ups(
                job_title=state.job_title,
                question_id=base_question_id or "",
                answer=state.answer_text,
            )
        except RuntimeError:
            state.workflow_trace.append("qwen_follow_up_enrichment_skipped")
            return

        if not follow_ups:
            return
        state.follow_up_questions = follow_ups
        state.workflow_trace.append("qwen_follow_up_enrichment_node")

    @staticmethod
    def _strengths(technical: int, structure: int, project: int) -> list[str]:
        strengths = []
        if technical >= 75:
            strengths.append("能覆盖岗位相关技术关键词。")
        if structure >= 75:
            strengths.append("回答有一定结构，便于面试官追问。")
        if project >= 75:
            strengths.append("能把技术实现和业务场景关联起来。")
        return strengths or ["回答具备基础信息，但需要补充更具体的项目证据。"]

    @staticmethod
    def _risks(technical: int, structure: int, risk: int) -> list[str]:
        risks = []
        if technical < 70:
            risks.append("技术细节偏少，容易被追问到实现时卡住。")
        if structure < 70:
            risks.append("回答结构不够稳定，需要按 背景-方案-结果-优化 组织。")
        if risk < 70:
            risks.append("生产化风险意识不足，需要补充监控、降级、扩容和测试。")
        return risks or ["主要风险较低，建议准备更量化的项目结果。"]
