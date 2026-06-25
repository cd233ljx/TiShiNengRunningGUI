"""里程查询。简化 main.py 中的实现：先取 sumExerciseRecord/sumSportRecord 汇总；若拿不到，再翻页累加。"""
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import TsnAccount_Model
from tsnClient import getTsnClientById
from webapp.deps import get_db, require_token

router = APIRouter(prefix="/api/distance", tags=["distance"],
                   dependencies=[Depends(require_token)])


class DistanceBody(BaseModel):
    account_id: int


@router.post("/query")
async def distance_query(body: DistanceBody, db: AsyncSession = Depends(get_db)) -> dict:
    stmt = (select(TsnAccount_Model)
            .options(selectinload(TsnAccount_Model.school))
            .where(TsnAccount_Model.id == body.account_id))
    acct = (await db.execute(stmt)).scalars().first()
    if not acct:
        raise HTTPException(status_code=404,
                            detail={"code": "ACCOUNT_NOT_FOUND", "msg": "账号不存在"})

    tsn = await getTsnClientById(body.account_id, db)
    total_km = 0.0
    count = 0
    try:
        if tsn.isPublic():
            summary = await tsn.sumExerciseRecord()
        else:
            summary = await tsn.sumSportRecord()
        if summary and "sportRange" in summary:
            total_km = float(summary["sportRange"])
            count = int(summary.get("sportTimes", 0) or 0)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"距离汇总失败，将返回 0: {e}")
    return {
        "total_km": round(total_km, 2),
        "count": count,
        "school_name": acct.school.school_name if acct.school else None,
        "username": acct.username,
    }
