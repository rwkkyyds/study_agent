"""简历解析服务：支持 text、markdown 和 PDF。"""

from __future__ import annotations

import re
from io import BytesIO

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.resume import ResumeProfile
from app.models.user import User
from app.schemas.resume import ResumeParseRequest


class ResumeParserService:
    """确定性简历解析器，阶段四可替换为 LLM/Agent 节点。"""

    SKILL_KEYWORDS = [
        "Python",
        "FastAPI",
        "SQLAlchemy",
        "PostgreSQL",
        "Redis",
        "Milvus",
        "Docker",
        "LangGraph",
        "RAG",
        "React",
        "Next.js",
        "Celery",
        "Kubernetes",
        "OpenAI",
        "LLM",
        "向量数据库",
        "知识库",
        "智能体",
        "后端",
        "前端",
    ]
    JOB_KEYWORDS = {
        "ai": ["LLM", "RAG", "Agent", "向量检索", "提示词工程"],
        "应用": ["FastAPI", "业务闭环", "接口设计", "部署"],
        "后端": ["API", "数据库", "缓存", "异步任务"],
        "全栈": ["前端", "后端", "接口联调", "用户体验"],
        "算法": ["模型评估", "特征", "召回", "排序"],
    }

    def parse_text(self, db: Session, current_user: User, request: ResumeParseRequest) -> ResumeProfile:
        """解析 text/markdown 简历并保存画像。"""

        normalized = self._normalize_text(request.content, request.content_type)
        return self._create_profile(
            db=db,
            current_user=current_user,
            raw_text=request.content,
            normalized_text=normalized,
            source_type=request.content_type,
            source_name=request.source_name,
            target_job_title=request.target_job_title,
        )

    async def parse_upload(
        self,
        db: Session,
        current_user: User,
        file: UploadFile,
        target_job_title: str | None = None,
    ) -> ResumeProfile:
        """解析上传的 text、markdown 或 PDF 文件并保存画像。"""

        content = await file.read()
        source_type = self._detect_source_type(file.filename or "", file.content_type or "")
        if source_type == "pdf":
            raw_text = self._extract_pdf_text(content)
        else:
            raw_text = content.decode("utf-8", errors="ignore")

        normalized = self._normalize_text(raw_text, source_type)
        return self._create_profile(
            db=db,
            current_user=current_user,
            raw_text=raw_text,
            normalized_text=normalized,
            source_type=source_type,
            source_name=file.filename,
            target_job_title=target_job_title,
        )

    @staticmethod
    def get_user_profile(db: Session, current_user: User, profile_id: int) -> ResumeProfile | None:
        """按当前用户读取画像。"""

        return db.query(ResumeProfile).filter(ResumeProfile.id == profile_id, ResumeProfile.user_id == current_user.id).first()

    def _create_profile(
        self,
        db: Session,
        current_user: User,
        raw_text: str,
        normalized_text: str,
        source_type: str,
        source_name: str | None,
        target_job_title: str | None,
    ) -> ResumeProfile:
        if len(normalized_text) < 20:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="简历正文过短，无法形成候选人画像")

        skills = self._extract_skills(normalized_text)
        projects = self._extract_projects(normalized_text)
        years = self._extract_years(normalized_text)
        target_keywords = self._extract_target_keywords(target_job_title, normalized_text)
        summary = self._build_summary(skills, projects, years, target_keywords)

        profile = ResumeProfile(
            user_id=current_user.id,
            source_type=source_type,
            source_name=source_name,
            raw_text=raw_text,
            normalized_text=normalized_text,
            summary=summary,
            skills=skills,
            projects=projects,
            years_of_experience=years,
            target_keywords=target_keywords,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def _detect_source_type(filename: str, content_type: str) -> str:
        name = filename.lower()
        if name.endswith(".pdf") or content_type == "application/pdf":
            return "pdf"
        if name.endswith(".md") or name.endswith(".markdown") or "markdown" in content_type:
            return "markdown"
        if name.endswith(".txt") or content_type.startswith("text/"):
            return "text"
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="仅支持 text、markdown、PDF 简历")

    @staticmethod
    def _normalize_text(content: str, source_type: str) -> str:
        text = content.replace("\r\n", "\n").replace("\r", "\n")
        if source_type == "markdown":
            text = re.sub(r"```.*?```", " ", text, flags=re.S)
            text = re.sub(r"[#>*_`~-]+", " ", text)
            text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _extract_pdf_text(content: bytes) -> str:
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="PDF 简历解析失败") from exc

    def _extract_skills(self, text: str) -> list[str]:
        lower_text = text.lower()
        skills = []
        for keyword in self.SKILL_KEYWORDS:
            if keyword.lower() in lower_text or keyword in text:
                skills.append(keyword)
        return sorted(set(skills), key=skills.index)

    @staticmethod
    def _extract_projects(text: str) -> list[str]:
        lines = [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
        project_lines = [
            line
            for line in lines
            if any(keyword in line for keyword in ["项目", "系统", "平台", "应用", "RAG", "Agent", "智能客服"])
        ]
        compact = []
        for line in project_lines:
            if len(line) > 120:
                line = line[:117] + "..."
            if line not in compact:
                compact.append(line)
        return compact[:5]

    @staticmethod
    def _extract_years(text: str) -> int | None:
        patterns = [
            r"(\d+)\s*年(?:以上)?(?:工作|开发|项目|经验)",
            r"工作(?:经验)?\s*(\d+)\s*年",
            r"(\d+)\s*\+\s*年",
            r"(\d+)\s*年.*?经验",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        return None

    def _extract_target_keywords(self, target_job_title: str | None, text: str) -> list[str]:
        candidates: list[str] = []
        if target_job_title:
            title = target_job_title.lower()
            for key, values in self.JOB_KEYWORDS.items():
                if key in title or key in target_job_title:
                    candidates.extend(values)
        candidates.extend(skill for skill in self._extract_skills(text) if skill in {"FastAPI", "RAG", "LangGraph", "Docker", "Redis"})
        return sorted(set(candidates), key=candidates.index)[:8]

    @staticmethod
    def _build_summary(skills: list[str], projects: list[str], years: int | None, target_keywords: list[str]) -> str:
        parts = []
        if years is not None:
            parts.append(f"{years} 年相关经验")
        if skills:
            parts.append("技能栈：" + "、".join(skills[:6]))
        if projects:
            parts.append(f"可深挖项目 {len(projects)} 个")
        if target_keywords:
            parts.append("岗位匹配关键词：" + "、".join(target_keywords[:5]))
        return "；".join(parts) if parts else "简历信息较少，需要通过基础项目题确认候选人能力。"


