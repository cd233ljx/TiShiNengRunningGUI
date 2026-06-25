"""学校列表与刷新。

GET  /api/schools           — 返回当前数据库中的学校
POST /api/schools/refresh   — 异步触发刷新，立即返回 task_id；
                              前端通过 /ws/progress 订阅 phase=refreshing/done 事件
"""
import asyncio
import uuid
from typing import Dict, Optional

import httpx
from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from TiShiNengSdkPrivate import TiShiNengPrivate
from database import get_db as _raw_get_db
from models import TsnSchool_Model
from services.tsnSchool.tsnSchoolDao import addOrUpdateSchool
from webapp.deps import get_db, require_token
from webapp.progress import bus

router = APIRouter(prefix="/api/schools", tags=["schools"], dependencies=[Depends(require_token)])

# 全局 task 注册表（与 run/spider 路由对齐）
_TASKS: Dict[str, asyncio.Task] = {}


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


async def _do_refresh(task_id: str) -> None:
    """后台异步刷新。每个省份完成后向 bus 推 phase=refreshing；全部完成推 done。"""
    # 让 POST 响应先返回、前端 WS 来得及订阅，再开始发事件（避免无缓冲 bus 丢首事件）。
    await asyncio.sleep(0.1)
    try:
        tsn = _make_client()
        resp = await tsn.findAllProvince()
        if not resp or 'data' not in resp:
            await bus.publish(task_id, {"phase": "done", "total": 0, "skipped": 0,
                                        "msg": "未获取到省份列表"})
            return

        provinces = resp['data']
        total = 0
        skipped = 0
        async with httpx.AsyncClient() as http:
            async for db in _raw_get_db():
                for idx, province in enumerate(provinces, 1):
                    province_name = province.get('province_name', '?')

                    # 进度事件：在开始处理本省前推
                    await bus.publish(task_id, {
                        "phase": "refreshing",
                        "current": idx,
                        "total": len(provinces),
                        "province": province_name,
                        "schools_added": total,
                    })

                    try:
                        plist = await tsn.listSchoolByProvinceId(province['province_id'])
                    except Exception as e:
                        logger.warning(f"获取省份 {province_name} 学校列表失败: {e}")
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
                    try:
                        await db.commit()
                    except Exception as e:
                        logger.warning(f"提交省份 {province_name} 失败: {e}")
                        await db.rollback()
                break  # 只用第一个 session（_raw_get_db 是 async generator）

        await bus.publish(task_id, {"phase": "done", "total": total, "skipped": skipped})
    except Exception as e:
        logger.exception(e)
        await bus.publish(task_id, {"phase": "error", "code": "UNKNOWN", "msg": str(e)})
    finally:
        _TASKS.pop(task_id, None)


@router.post("/refresh")
async def refresh_schools() -> dict:
    """立即返回 task_id；后台异步刷新。前端通过 /ws/progress?task=<id> 订阅进度。"""
    task_id = uuid.uuid4().hex
    _TASKS[task_id] = asyncio.create_task(_do_refresh(task_id))
    return {"task_id": task_id}
