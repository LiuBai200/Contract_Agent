import re

from langchain_core.documents import Document

from backend.schemas import ChunkPreview


CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

CLAUSE_PATTERN = re.compile(
    r"(?=(第[一二三四五六七八九十百千万零〇0-9]+[条章节款项][^\n。；;:：]{0,40}|"
    r"(?:甲方义务|乙方义务|双方义务|付款方式|付款条款|交付方式|交付验收|验收标准|"
    r"违约责任|保密条款|知识产权|争议解决|合同解除|合同期限|生效条件|不可抗力|"
    r"服务内容|费用结算|风险提示)[：:]?))"
)


def split_contract_documents(documents: list[Document]) -> list[Document]:
    chunks: list[Document] = []

    for doc in documents:
        blocks = _split_by_contract_rules(doc.page_content)
        if not blocks:
            blocks = [doc.page_content]

        for block in blocks:
            for piece in _split_long_text(block, CHUNK_SIZE, CHUNK_OVERLAP):
                content = piece.strip()
                if not content:
                    continue

                metadata = dict(doc.metadata)
                metadata["chunk_index"] = len(chunks) + 1
                metadata["split_strategy"] = "contract_rule_then_size"
                clause_title = _extract_clause_title(content)
                if clause_title:
                    metadata["clause_title"] = clause_title

                chunks.append(Document(page_content=content, metadata=metadata))

    return chunks


def chunks_to_preview(chunks: list[Document], max_items: int = 5, max_chars: int = 500) -> list[ChunkPreview]:
    previews = []
    for chunk in chunks[:max_items]:
        content = chunk.page_content
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        previews.append(ChunkPreview(page_content=content, metadata=dict(chunk.metadata)))
    return previews


def _split_by_contract_rules(text: str) -> list[str]:
    normalized = _normalize_text(text)
    matches = list(CLAUSE_PATTERN.finditer(normalized))

    if not matches:
        return [normalized] if normalized else []

    blocks: list[str] = []
    first_start = matches[0].start()
    if first_start > 0:
        prefix = normalized[:first_start].strip()
        if prefix:
            blocks.append(prefix)

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        block = normalized[start:end].strip()
        if block:
            blocks.append(block)

    return blocks


def _split_long_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def _extract_clause_title(text: str) -> str | None:
    first_line = text.splitlines()[0].strip()
    if len(first_line) > 60:
        first_line = first_line[:60]
    return first_line or None


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
