"""知识库文档管理 API。"""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Chunk, Document
from app.models.user import User
from app.rag.chunker import TextChunker
from app.rag.retriever import Retriever, get_shared_retriever
from app.services.auth import require_any_role, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def get_retriever() -> Retriever:
    """提供默认检索服务，与 chat API 共享。"""

    return get_shared_retriever()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_document(
    title: str,
    content: str,
    source: str = "manual",
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    retriever: Retriever = Depends(get_retriever),
) -> dict:
    """上传知识库文档，自动切分、向量化并存入检索索引。"""

    if not title.strip() or not content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="文档标题和内容不能为空",
        )

    doc = Document(title=title.strip(), content=content.strip(), source=source)
    try:
        db.add(doc)
        db.flush()

        # 切分并向量化。索引失败时回滚文档写入，避免数据库与向量库不一致。
        chunker = TextChunker()
        chunks = chunker.split_text(content)
        if chunks:
            chunk_data = [
                (f"doc-{doc.id}-chunk-{c.chunk_index}", c.content, {"document_id": doc.id, "title": title})
                for c in chunks
            ]
            written = retriever.index_chunks(chunk_data)

            for c in chunks:
                db.add(Chunk(document_id=doc.id, content=c.content, chunk_index=c.chunk_index))
        else:
            written = 0

        db.commit()
        db.refresh(doc)
    except Exception:
        db.rollback()
        raise

    logger.info("文档上传成功 id=%d title=%s chunks=%d", doc.id, title, written)
    return {
        "id": doc.id,
        "title": doc.title,
        "chunks": written,
        "message": "文档上传并索引成功",
    }


@router.get("")
def list_documents(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_any_role("agent", "admin")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """列出知识库文档。"""

    docs = db.query(Document).offset(skip).limit(limit).all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "source": d.source,
            "chunk_count": len(d.chunks),
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    retriever: Retriever = Depends(get_retriever),
) -> None:
    """删除文档及其切分块。需要 admin 角色。"""

    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )
    chunk_ids = [f"doc-{doc.id}-chunk-{chunk.chunk_index}" for chunk in doc.chunks]
    try:
        retriever.delete_chunks(chunk_ids)
    except Exception as exc:
        logger.warning("文档向量索引删除失败 id=%d: %s", doc_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="文档向量索引删除失败，请稍后重试",
        ) from exc
    db.delete(doc)
    db.commit()
    logger.info("文档已删除 id=%d", doc_id)
