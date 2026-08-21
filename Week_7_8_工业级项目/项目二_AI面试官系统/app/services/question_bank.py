"""岗位题库检索服务。"""

from __future__ import annotations

from app.knowledge.question_bank import QUESTION_BANK
from app.schemas.interview import InterviewQuestion
from app.schemas.question_bank import QuestionBankItemResponse, QuestionBankSearchRequest, QuestionBankSearchResponse


class QuestionBankRetriever:
    """本地 RAG 检索器，后续可替换为向量数据库。"""

    JOB_KEYWORDS = {
        "ai": ["RAG", "Agent", "LLM", "向量", "评估"],
        "智能": ["RAG", "Agent", "LLM", "向量"],
        "后端": ["FastAPI", "SQLAlchemy", "JWT", "数据库", "缓存"],
        "开发": ["FastAPI", "Docker", "部署", "测试"],
        "全栈": ["React", "FastAPI", "接口", "状态管理"],
        "前端": ["React", "前端", "状态管理", "报告"],
        "架构": ["系统设计", "并发", "缓存", "队列"],
    }

    def search(self, request: QuestionBankSearchRequest) -> QuestionBankSearchResponse:
        """按岗位、简历和难度检索题库。"""

        query_keywords = self.extract_query_keywords(request.job_title, request.resume_text or "")
        ranked_items = self._rank_items(query_keywords=query_keywords, difficulty=request.difficulty)
        return QuestionBankSearchResponse(
            query_keywords=query_keywords,
            items=[self._to_response(item, score) for item, score in ranked_items[: request.top_k]],
        )

    def retrieve_for_interview(self, job_title: str, resume_text: str, difficulty: str, top_k: int = 3) -> list[InterviewQuestion]:
        """返回可直接混入面试题生成链路的题目。"""

        response = self.search(
            QuestionBankSearchRequest(
                job_title=job_title,
                resume_text=resume_text,
                difficulty=difficulty,
                top_k=top_k,
            )
        )
        return [
            InterviewQuestion(
                id=f"kb{index + 1}",
                question_type=item.question_type,
                question=item.question,
                expected_points=item.expected_points,
                source=f"{item.source} | score={item.score}",
            )
            for index, item in enumerate(response.items)
        ]

    def extract_query_keywords(self, job_title: str, resume_text: str) -> list[str]:
        """从岗位和简历中抽取检索关键词。"""

        keywords: list[str] = []
        title_lower = job_title.lower()
        for key, values in self.JOB_KEYWORDS.items():
            if key in title_lower or key in job_title:
                keywords.extend(values)

        text_lower = resume_text.lower()
        for item in QUESTION_BANK:
            for keyword in item["keywords"]:
                if keyword.lower() in text_lower or keyword in resume_text:
                    keywords.append(keyword)
        return sorted(set(keywords), key=keywords.index)

    @staticmethod
    def _to_response(item: dict, score: int) -> QuestionBankItemResponse:
        return QuestionBankItemResponse(
            id=item["id"],
            skill=item["skill"],
            difficulty=item["difficulty"],
            question_type=item["question_type"],
            question=item["question"],
            expected_points=item["expected_points"],
            keywords=item["keywords"],
            source=item["source"],
            score=score,
        )

    def _rank_items(self, query_keywords: list[str], difficulty: str) -> list[tuple[dict, int]]:
        ranked: list[tuple[dict, int]] = []
        query = {keyword.lower() for keyword in query_keywords}
        for item in QUESTION_BANK:
            item_keywords = {keyword.lower() for keyword in item["keywords"]}
            overlap = len(query & item_keywords)
            difficulty_score = 2 if item["difficulty"] == difficulty else 1 if item["difficulty"] == "mid" else 0
            score = overlap * 10 + difficulty_score
            if score > 0:
                ranked.append((item, score))
        return sorted(ranked, key=lambda value: (-value[1], value[0]["id"]))

