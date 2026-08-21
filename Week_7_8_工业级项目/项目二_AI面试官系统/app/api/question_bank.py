"""岗位题库检索 API。"""

from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.question_bank import QuestionBankSearchRequest, QuestionBankSearchResponse
from app.services.auth import get_current_user
from app.services.question_bank import QuestionBankRetriever

router = APIRouter(prefix="/question-bank", tags=["question-bank"])
retriever = QuestionBankRetriever()


@router.post("/search", response_model=QuestionBankSearchResponse)
def search_question_bank(
    request: QuestionBankSearchRequest,
    current_user: User = Depends(get_current_user),
) -> QuestionBankSearchResponse:
    """按岗位、简历关键词和难度检索题库。"""

    return retriever.search(request)

