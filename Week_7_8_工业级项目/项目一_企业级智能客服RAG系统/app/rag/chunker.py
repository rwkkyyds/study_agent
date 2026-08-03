"""文档分块：将文档原文切分为适合检索的块。

支持按字符数、段落、或固定长度分块。
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TextChunker:
    """文本分块器。

    将长文本按指定大小和重叠切分为多个块，
    保证语义完整性和检索覆盖度。
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(
            "TextChunker initialized: size=%d, overlap=%d",
            chunk_size, chunk_overlap,
        )

    def split_text(self, text: str, metadata: Optional[dict] = None) -> list[dict]:
        """将文本切分为块，返回 [{content, index, metadata}, ...]。"""

        if not text.strip():
            return []

        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            meta = dict(metadata) if metadata else {}
            meta.update({"chunk_start": start, "chunk_end": end})
            chunks.append({
                "content": chunk_text,
                "index": index,
                "metadata": meta,
            })

            index += 1
            next_start = end - self.chunk_overlap
            if next_start <= start:  # 防止无限循环
                next_start = end
            start = next_start

        logger.info("Split text into %d chunks (size=%d, overlap=%d)", len(chunks), self.chunk_size, self.chunk_overlap)
        return chunks