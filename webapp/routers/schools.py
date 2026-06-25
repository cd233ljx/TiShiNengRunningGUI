"""学校列表与刷新。

GET  /api/schools           — 返回当前数据库中的学校
POST /api/schools/refresh   — 调用 SDK 重新拉取并落库
"""
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from TiShiNengSdkPrivate import TiShiNengPrivate
from models import TsnSchool_Model
from services.tsnSchool.tsnSchoolDao import addOrUpdateSchool
from webapp.deps import get_db, require_token

router = APIRouter(prefix="/api/schools", tags=["schools"], dependencies=[Depends(require_token)])


def _make_client() -> TiShiNengPrivate:
    """构造一个匿名 SDK 客户端用于查询省份/学校列表。可被测试 patch。"""
    return TiShiNengPrivate(1, 1, '', False, str(uuid.uuid4()), 'Xiaomi', '25053RT47C', "")


async def _get_school_info_async(school_code: str, client: httpx.AsyncClient) -> Optional[dict]:
    """对公版学校请求内网 URL。失败返回 None。复用调用方的 AsyncClient 连接池。"""
    try:
        url = f"https://h.tsnkj.com/upms/sysSchool/getSchoolInfo?schoolCode={school_code}"
        resp = await client.get(url, headers={"User-Agent": "okhttp/4.9.0"}, timeout=10.0)
        return resp.json().get("data")
    except Exception as e:
        logger.debug(f"_get_school_info failed for {school_code}: {e}")
        return None


@router.get("")
async def list_schools(db: AsyncSession = Depends(get_db)) -> dict:
    stmt = select(TsnSchool_Model).order_by(TsnSchool_Model.school_name)
    result = await db.execute(stmt)
    items = []
    for s in result.scalars().all():
        items.append({
            "school_id": s.school_id,
            "school_name": s.school_name,
            "sys_type": s.sys_type,  # 1 私版, 2 公版
            "school_code": s.school_code,
        })
    return {"items": items}


@router.post("/refresh")
async def refresh_schools(db: AsyncSession = Depends(get_db)) -> dict:
    tsn = _make_client()
    resp = await tsn.findAllProvince()
    if not resp or 'data' not in resp:
        return {"total": 0, "msg": "未获取到省份列表"}

    total = 0
    skipped = 0
    async with httpx.AsyncClient() as http:
        for province in resp['data']:
            try:
                plist = await tsn.listSchoolByProvinceId(province['province_id'])
            except Exception as e:
                logger.warning(f"获取省份 {province.get('province_name')} 学校列表失败: {e}")
                skipped += 1
                continue
            if not plist or 'data' not in plist:
                continue
            for school in plist['data']:
                name = school['school_name']
                if 'demo' in name.lower() or 'test' in name.lower():
                    continue
                lan_url = None
                if school['sysType'] == '2':
                    info = await _get_school_info_async(school['schoolCode'], http)
                    if info and info.get("url"):
                        lan_url = f"https://{info['url']}"
                try:
                    await addOrUpdateSchool(
                        school['school_id'], school['school_name'], school['school_url'],
                        lan_url, school['openId'],
                        school['isOpenKeep'] == '1',
                        school['isOpenLive'] == '1',
                        school['isOpenEncry'] == '1',
                        int(school['sysType']), school['schoolCode'], db,
                    )
                    total += 1
                except Exception as e:
                    logger.warning(f"写入学校 {name} 失败: {e}")
                    skipped += 1
                    continue
            # 每个省份处理完 commit 一次，缩短事务持有时间
            try:
                await db.commit()
            except Exception as e:
                logger.warning(f"提交省份 {province.get('province_name')} 失败: {e}")
                await db.rollback()

    return {"total": total, "skipped": skipped}
