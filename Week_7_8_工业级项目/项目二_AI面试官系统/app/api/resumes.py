"""简历解析 API。"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.resume import ResumeParseRequest, ResumeProfileResponse
from app.services.auth import get_current_user
from app.services.resume_parser import ResumeParserService

router = APIRouter(prefix="/resumes", tags=["resumes"])
resume_service = ResumeParserService()


@router.post("/parse", response_model=ResumeProfileResponse, status_code=status.HTTP_201_CREATED)
def parse_resume_text(
    request: ResumeParseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeProfileResponse:
    """解析 text/markdown 简历并保存候选人画像。"""

    return resume_service.parse_text(db=db, current_user=current_user, request=request)


@router.post("/upload", response_model=ResumeProfileResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    target_job_title: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeProfileResponse:
    """上传 text、markdown 或 PDF 简历并保存候选人画像。"""

    return await resume_service.parse_upload(db=db, current_user=current_user, file=file, target_job_title=target_job_title)


@router.get("/{profile_id}", response_model=ResumeProfileResponse)
def get_resume_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeProfileResponse:
    """读取当前用户自己的候选人画像。"""

    profile = resume_service.get_user_profile(db=db, current_user=current_user, profile_id=profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="候选人画像不存在")
    return profile
