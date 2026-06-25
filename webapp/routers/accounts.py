"""账号 CRUD + 授权。"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import TsnAccount_Model
from tsnClient import tsnPasswordAuthServer
from webapp.deps import get_db, require_token

router = APIRouter(prefix="/api/accounts", tags=["accounts"],
                   dependencies=[Depends(require_token)])


class AuthorizeBody(BaseModel):
    school_id: int = Field(..., description="学校 ID（来自 /api/schools）")
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


def _serialize(acct: TsnAccount_Model) -> dict:
    return {
        "id": acct.id,
        "username": acct.username,
        "school_id": acct.school_id,
        "school_name": acct.school.school_name if acct.school else None,
        "sys_type": acct.school.sys_type if acct.school else None,
    }


@router.get("")
async def list_accounts(db: AsyncSession = Depends(get_db)) -> dict:
    stmt = select(TsnAccount_Model).options(selectinload(TsnAccount_Model.school))
    result = await db.execute(stmt)
    items = [_serialize(a) for a in result.scalars().all()]
    return {"items": items}


@router.post("/authorize")
async def authorize(body: AuthorizeBody, db: AsyncSession = Depends(get_db)) -> dict:
    # 失败由全局异常处理器返回 {code, msg}
    uid = await tsnPasswordAuthServer(body.school_id, body.username, body.password, db)
    # 取回刚刚保存的账号
    stmt = (select(TsnAccount_Model)
            .options(selectinload(TsnAccount_Model.school))
            .where(TsnAccount_Model.username == body.username,
                   TsnAccount_Model.school_id == body.school_id))
    acct = (await db.execute(stmt)).scalars().first()
    if not acct:
        raise HTTPException(status_code=500,
                            detail={"code": "POST_AUTH_LOOKUP_FAILED",
                                    "msg": f"授权成功但未找到账号记录(uid={uid})"})
    return {"account_id": acct.id, **_serialize(acct)}


@router.delete("/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    stmt = select(TsnAccount_Model).where(TsnAccount_Model.id == account_id)
    acct = (await db.execute(stmt)).scalars().first()
    if not acct:
        raise HTTPException(status_code=404,
                            detail={"code": "ACCOUNT_NOT_FOUND", "msg": "账号不存在"})
    await db.execute(delete(TsnAccount_Model).where(TsnAccount_Model.id == account_id))
    await db.flush()
    return {"deleted": True}
