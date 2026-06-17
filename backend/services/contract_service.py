from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models import ContractFile, User
from backend.schemas import ContractDeleteResponse, ContractSummary, UploadResponse
from backend.services.contract_splitter import chunks_to_preview, split_contract_documents
from backend.services.document_loader import documents_to_preview, load_file_to_documents
from backend.services.upload_service import save_upload_file
from backend.services.vector_store import VectorStoreService


async def upload_contract_for_user(file: UploadFile, user: User, db: Session) -> UploadResponse:
    result = await save_upload_file(file, settings.upload_dir)

    contract = ContractFile(
        user_id=user.id,
        filename=result.filename,
        saved_path=result.saved_path,
        size=result.size,
        content_type=result.content_type,
    )
    db.add(contract)
    db.flush()

    documents = load_file_to_documents(result.saved_path, result.filename)
    for doc in documents:
        doc.metadata["user_id"] = str(user.id)
        doc.metadata["contract_id"] = str(contract.id)

    chunks = split_contract_documents(documents)
    stored_count = await VectorStoreService().add_documents(chunks)

    contract.document_count = len(documents)
    contract.chunk_count = len(chunks)
    db.commit()
    db.refresh(contract)

    result.contract_id = contract.id
    result.document_count = len(documents)
    result.documents = documents_to_preview(documents)
    result.chunk_count = len(chunks)
    result.stored_count = stored_count
    result.chunks = chunks_to_preview(chunks)
    result.message = (
        f"文件已保存、解析、切分并写入 ChromaDB。"
        f"Document 数: {len(documents)}，切片数: {len(chunks)}，入库数: {stored_count}。"
    )
    return result


def list_contracts_for_user(user_id: int, db: Session) -> list[ContractSummary]:
    contracts = (
        db.query(ContractFile)
        .filter(ContractFile.user_id == user_id)
        .order_by(ContractFile.created_at.desc())
        .all()
    )
    return [
        ContractSummary(
            id=contract.id,
            filename=contract.filename,
            size=contract.size,
            document_count=contract.document_count,
            chunk_count=contract.chunk_count,
            created_at=contract.created_at.isoformat(),
        )
        for contract in contracts
    ]


async def delete_contract_for_user(
    contract_id: int,
    user_id: int,
    db: Session,
) -> ContractDeleteResponse | None:
    contract = (
        db.query(ContractFile)
        .filter(ContractFile.id == contract_id, ContractFile.user_id == user_id)
        .first()
    )
    if not contract:
        return None

    filename = contract.filename
    deleted_chunks = contract.chunk_count
    saved_path = Path(contract.saved_path)

    await VectorStoreService().delete_contract(user_id=user_id, contract_id=contract.id)

    if saved_path.is_file():
        saved_path.unlink()

    db.delete(contract)
    db.commit()
    return ContractDeleteResponse(
        contract_id=contract_id,
        filename=filename,
        deleted_chunks=deleted_chunks,
        message=f"已删除合同：{filename}",
    )
