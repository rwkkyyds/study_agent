"""文档切分器。

阶段三采用确定性的字符窗口切分，后续可在不改变服务层接口的前提下替换为
Markdown、HTML 或按语义切分策略。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    """切分后的文本块及其在原文中的顺序。"""

    content: str
    chunk_index: int


class TextChunker:
    """使用固定窗口和重叠区域切分文本。"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须大于等于 0 且小于 chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> list[TextChunk]:
        """返回非空切分块；空白文本返回空列表。"""

        if not isinstance(text, str):
            raise TypeError("text 必须是字符串")
        normalized = text.strip()
        if not normalized:
            return []

        step = self.chunk_size - self.chunk_overlap
        chunks: list[TextChunk] = []
        for index, start in enumerate(range(0, len(normalized), step)):
            content = normalized[start : start + self.chunk_size].strip()
            if content:
                chunks.append(TextChunk(content=content, chunk_index=index))
        return chunks
