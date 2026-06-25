"""更新人脸图片端点。复用 TsnRunServer.getFaceImage（会自动下载并落盘）。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import TsnAccount_Model
from tsnClient import getTsnClientById
from tsnRunServer import TsnRunServer, TsnRunType
from webapp.deps import get_db, require_token

router = APIRouter(prefix="/api/face", tags=["face"],
                   dependencies=[Depends(require_token)])


class FaceUpdateBody(BaseModel):
    account_id: int


@router.post("/update")
async def face_update(body: FaceUpdateBody, db: AsyncSession = Depends(get_db)) -> dict:
    stmt = (select(TsnAccount_Model)
            .options(selectinload(TsnAccount_Model.school))
            .where(TsnAccount_Model.id == body.account_id))
    acct = (await db.execute(stmt)).scalars().first()
    if not acct:
        raise HTTPException(status_code=404,
                            detail={"code": "ACCOUNT_NOT_FOUND", "msg": "账号不存在"})

    server = TsnRunServer(accountId=body.account_id, runKiloMeter=1.0,
                          logRunType=TsnRunType.freedom)
    server.accountModel = acct
    server.tsnClient = await getTsnClientById(acct.id, db)
    server.isPublic = server.tsnClient.isPublic()

    image_bytes = await server.getFaceImage()
    return {"updated": bool(image_bytes), "size": len(image_bytes) if image_bytes else 0}
