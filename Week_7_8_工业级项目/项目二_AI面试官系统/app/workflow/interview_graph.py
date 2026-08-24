"""阶段五图式面试工作流。

当前用本地确定性节点模拟 LangGraph 的 StateGraph 思路：
state -> node -> state -> conditional node -> output。
阶段五加入本地岗位题库检索节点，模拟后续向量库/RAG 召回。
"""

from __future__ import annotations

import hashlib
import re
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
    base_question_text: str = ""
    answer_text: str = ""
    answer_relevance: int = 0
    dimension_scores: dict[str, int] = field(default_factory=dict)
    follow_up_questions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    learning_suggestions: list[str] = field(default_factory=list)
    workflow_trace: list[str] = field(default_factory=list)


class InterviewWorkflow:
    """AI 面试官图式工作流门面。"""

    DEFAULT_SCORE_WEIGHTS: dict[str, float] = {
        "technical": 0.35,
        "structure": 0.25,
        "project": 0.25,
        "risk": 0.15,
    }
    SCORE_DIMENSION_META: dict[str, tuple[str, str]] = {
        "technical": ("技术匹配度", "是否能讲清岗位核心技术栈和实现细节。"),
        "structure": ("表达结构", "回答是否有层次、有原因、有取舍。"),
        "project": ("项目理解", "是否能从业务闭环而不是单点 API 解释项目。"),
        "risk": ("风险意识", "是否能主动说明不足、监控、降级和后续优化。"),
    }
    RUBRIC_DIMENSION_ALIASES: dict[str, tuple[str, ...]] = {
        "technical": ("technical", "技术", "技能", "工程", "架构", "系统", "后端", "算法"),
        "structure": ("structure", "communication", "表达", "沟通", "结构", "逻辑"),
        "project": ("project", "项目", "业务", "经验", "场景", "产品", "交付"),
        "risk": ("risk", "风险", "稳定", "生产", "可靠", "监控", "降级", "扩展", "安全", "质量"),
    }

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

    def generate_follow_up(
        self,
        request: InterviewFollowUpRequest,
        job_title: str,
        question_text: str = "",
    ) -> InterviewFollowUpResponse:
        """运行：候选人回答 -> 追问生成。"""

        state = InterviewGraphState(
            job_title=job_title,
            base_question_text=question_text.strip(),
            answer_text=request.answer.strip(),
        )
        self._answer_analysis_node(state)
        self._follow_up_node(state, base_question_id=request.question_id)
        reason = self._follow_up_reason(state)
        return InterviewFollowUpResponse(
            session_id=request.session_id,
            question_id=request.question_id,
            follow_up_questions=state.follow_up_questions,
            reason=reason,
            workflow_trace=state.workflow_trace,
        )

    def evaluate_answers(
        self,
        request: AnswerSubmissionRequest,
        rubric_dimensions: list[dict[str, object]] | None = None,
        rubric_weights: dict[str, float] | None = None,
    ) -> InterviewReportResponse:
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
        overall, dimensions, used_rubric = self._build_weighted_report(
            scores=scores,
            rubric_dimensions=rubric_dimensions,
            rubric_weights=rubric_weights,
        )
        if used_rubric:
            state.workflow_trace.append("rubric_weighting_node")
        return InterviewReportResponse(
            session_id=request.session_id,
            overall_score=overall,
            level=self._level(overall),
            dimensions=dimensions,
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
        state.answer_relevance = self._answer_relevance(
            state.base_question_text,
            state.answer_text,
        )
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
        if state.base_question_text and state.answer_relevance < 35:
            follow_ups.append(
                f"你的回答还没有回应原题“{self._short_question(state.base_question_text)}”，"
                "请直接说明这个项目解决了什么业务问题、你负责了哪一部分以及最终结果。"
            )
        elif scores.get("technical", 0) < 70:
            follow_ups.append("请补充一个你亲自实现的关键技术细节，并说明为什么这样设计。")
        if state.answer_relevance >= 35 and scores.get("structure", 0) < 70:
            follow_ups.append("请按 背景-方案-结果-复盘 重新组织一次回答。")
        if state.answer_relevance >= 35 and scores.get("risk", 0) < 70:
            follow_ups.append("如果这个方案上线后出现故障，你会如何监控、降级和回滚？")
        if not follow_ups:
            follow_ups.append("请给出一个量化指标，证明这个项目不是只停留在 demo。")
        if base_question_id and state.answer_relevance >= 35 and len(follow_ups) < 2:
            follow_ups.append(f"针对 {base_question_id}，请补充你在项目中的个人贡献边界。")
        state.follow_up_questions = follow_ups[:2]
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

    @classmethod
    def _build_weighted_report(
        cls,
        scores: dict[str, int],
        rubric_dimensions: list[dict[str, object]] | None,
        rubric_weights: dict[str, float] | None,
    ) -> tuple[int, list[ScoreDimension], bool]:
        rubric_items = cls._resolve_rubric_score_items(rubric_dimensions, rubric_weights)
        if rubric_items:
            total_weight = sum(weight for _, _, weight in rubric_items)
            overall = round(sum(scores[key] * weight for _, key, weight in rubric_items) / total_weight)
            dimensions = [
                ScoreDimension(
                    name=name,
                    score=scores[key],
                    comment=f"按评分标准权重 {weight / total_weight:.1%} 计入总分，映射到底层维度：{cls.SCORE_DIMENSION_META[key][0]}。",
                )
                for name, key, weight in rubric_items
            ]
            return overall, dimensions, True

        dimensions = [
            ScoreDimension(name=name, score=scores[key], comment=comment)
            for key, weight in cls.DEFAULT_SCORE_WEIGHTS.items()
            for name, comment in [cls.SCORE_DIMENSION_META[key]]
        ]
        overall = round(sum(scores[key] * weight for key, weight in cls.DEFAULT_SCORE_WEIGHTS.items()))
        return overall, dimensions, False

    @classmethod
    def _resolve_rubric_score_items(
        cls,
        rubric_dimensions: list[dict[str, object]] | None,
        rubric_weights: dict[str, float] | None,
    ) -> list[tuple[str, str, float]]:
        if not rubric_dimensions and not rubric_weights:
            return []

        items: list[tuple[str, str, float]] = []
        seen_names: set[str] = set()
        weights = rubric_weights or {}

        for dimension in rubric_dimensions or []:
            raw_name = dimension.get("name") or dimension.get("key")
            name = str(raw_name).strip() if raw_name is not None else ""
            if not name:
                continue
            weight = cls._positive_float(weights.get(name, dimension.get("weight")))
            score_key = cls._score_key_for_rubric_dimension(name)
            if weight is None or score_key is None:
                continue
            items.append((name, score_key, weight))
            seen_names.add(name)

        for name, raw_weight in weights.items():
            if name in seen_names:
                continue
            score_key = cls._score_key_for_rubric_dimension(name)
            weight = cls._positive_float(raw_weight)
            if score_key is None or weight is None:
                continue
            items.append((name, score_key, weight))

        return items

    @classmethod
    def _score_key_for_rubric_dimension(cls, name: str) -> str | None:
        normalized = name.strip().lower()
        for score_key, aliases in cls.RUBRIC_DIMENSION_ALIASES.items():
            if any(alias in normalized for alias in aliases):
                return score_key
        return None

    @staticmethod
    def _positive_float(value: object) -> float | None:
        try:
            weight = float(value)
        except (TypeError, ValueError):
            return None
        if weight <= 0:
            return None
        return weight

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
                question=state.base_question_text,
                answer=state.answer_text,
            )
        except RuntimeError:
            state.workflow_trace.append("qwen_follow_up_enrichment_skipped")
            return

        if not follow_ups:
            return
        state.follow_up_questions = follow_ups
        state.workflow_trace.append("qwen_follow_up_enrichment_node")

    @classmethod
    def _answer_relevance(cls, question: str, answer: str) -> int:
        """用原题和回答的关键词交集估算是否答到了题目。"""

        if not question.strip():
            return 100
        question_tokens = cls._text_tokens(question)
        answer_tokens = cls._text_tokens(answer)
        if not question_tokens:
            return 100
        hits = len(question_tokens & answer_tokens)
        if hits == 0:
            return 0
        if hits == 1:
            return 35
        if hits <= 3:
            return 60
        return 80

    @staticmethod
    def _text_tokens(text: str) -> set[str]:
        tokens = {
            token.lower()
            for token in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]*", text)
        }
        cjk_chunks = re.findall(r"[\u4e00-\u9fff]+", text)
        for chunk in cjk_chunks:
            tokens.update(chunk[index:index + 2] for index in range(len(chunk) - 1))
        stopwords = {
            "请用", "分钟", "介绍", "你的", "最能", "代表", "能力", "并说",
            "说明", "什么", "这个", "岗位", "结合", "经历", "一个", "以及",
        }
        return {token for token in tokens if token not in stopwords and len(token) > 1}

    @staticmethod
    def _short_question(question: str, limit: int = 42) -> str:
        compact = " ".join(question.split())
        return compact if len(compact) <= limit else f"{compact[:limit]}..."

    @staticmethod
    def _follow_up_reason(state: InterviewGraphState) -> str:
        if state.base_question_text and state.answer_relevance < 35:
            return "回答与当前题目关联度较低，先要求候选人回到原题并补充业务、个人贡献和结果。"
        if state.answer_relevance < 60:
            return "回答触及了部分题目关键词，但技术细节或表达结构仍不完整。"
        return "根据当前题目和回答中缺失的技术细节、结果指标或风险意识生成追问。"

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
