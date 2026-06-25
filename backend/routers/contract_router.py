from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models import User
from backend.db.session import get_db
from backend.schemas import ContractDeleteResponse, ContractSummary, UploadResponse
from backend.security.dependencies import get_current_user
from backend.services.contract_service import delete_contract_for_user, list_contracts_for_user, upload_contract_for_user
from backend.services.rate_limiter import rate_limit


router = APIRouter(tags=["contracts"])


@router.post("/upload", response_model=UploadResponse)
@router.post("/contracts/upload", response_model=UploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    _: None = Depends(
        rate_limit(
            "upload",
            limit=settings.upload_rate_limit,
            window_seconds=settings.upload_rate_limit_window_seconds,
        )
    ),
    db: Session = Depends(get_db),
):
    try:
        return await upload_contract_for_user(file, current_user, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/contracts", response_model=list[ContractSummary])
async def get_contracts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_contracts_for_user(current_user.id, db)


@router.delete("/contracts/{contract_id}", response_model=ContractDeleteResponse)
async def delete_contract(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await delete_contract_for_user(contract_id, current_user.id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Contract not found")
    return result
