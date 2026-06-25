import json
from typing import Callable, Optional

from loguru import logger
from sqlalchemy import select, func

from TiShiNengSdkPrivate import TiShiNengPrivate
from TiShiNengSdkPublic import TiShiNengSdkPublic
from database import get_db
from models import RunPath
from tsnClient import getTsnClientById
from TiShiNengRunPathManage import getPointListDistance


async def AddDateBase(runPathId, runLineList, sportRange, pointIdList, okPointListJson, schoolCode, isPublic=True):
    """
    将跑步路径数据存入 SQLite 数据库

    Args:
        runPathId: 跑步路径ID
        runLineList: 路线坐标列表 [[lng, lat], ...]
        sportRange: 运动距离(公里)
        pointIdList: 打卡点ID列表
        okPointListJson: 已打卡点JSON字符串
        schoolCode: 学校代码
        isPublic: 是否公开版本
    """
    async for db in get_db():
        # 检查是否已存在
        if isPublic:
            stmt = select(func.count(RunPath.id)).where(
                RunPath.run_path_id == str(runPathId)
            )
        else:
            stmt = select(func.count(RunPath.id)).where(
                RunPath.run_path_id == str(runPathId),
                RunPath.school_code == schoolCode
            )

        result = await db.execute(stmt)
        isExist = result.scalar()

        if isExist > 0:
            logger.info(f"RunPath {runPathId} already exists, skipping")
            return

        # 取前5%的点计算距离
        repeatPointList = runLineList[:int(len(runLineList) * 0.05)]

        repeatPointListDistance = getPointListDistance(repeatPointList)

        if repeatPointListDistance < 0.1:
            logger.info(f"RunPath {runPathId} distance too short: {repeatPointListDistance}, skipping")
            return

        # 检查该学校的路径数量
        school_count_stmt = select(func.count(RunPath.id)).where(
            RunPath.school_code == schoolCode
        )
        result = await db.execute(school_count_stmt)
        schoolCount = result.scalar()

        if schoolCount > 10000:
            logger.info(f"School {schoolCode} has too many paths ({schoolCount}), skipping")
            return

        runLinePathJson = json.dumps(runLineList, ensure_ascii=False)

        # 创建新的路径记录
        runPath = RunPath(
            run_path_id=str(runPathId),
            school_code=schoolCode,
            sport_range=float(sportRange),
            run_line_path=runLinePathJson,
            point_id_list=json.dumps(pointIdList, ensure_ascii=False) if pointIdList else None,
            ok_point_list_json=okPointListJson,
            is_public=isPublic
        )

        db.add(runPath)
        await db.commit()
        await db.refresh(runPath)

        logger.info(f"AddDateBase success: runPathId={runPathId}, id={runPath.id}, school={schoolCode}")


async def processRawAndAddDateBase(schoolCode, rawData, isPublic=True):
    runPathId = str(rawData['id'])
    sportRange = rawData['sportRange']
    okPointList = rawData['okPointList']
    if okPointList is None:
        okPointList = []
    okPointListJson = json.dumps(okPointList)
    print(okPointList)

    pointIdList = [i['id'] if "id" in i else int(i) for i in okPointList]
    gitudeLatitude = rawData['gitudeLatitude']
    if len(gitudeLatitude) == 0:
        return
    if isPublic:
        runLineList = [[float(i['o']), float(i['a'])] for i in gitudeLatitude]
    else:
        runLineList = [[float(i['longitude']), float(i['latitude'])] for i in gitudeLatitude]
    await AddDateBase(runPathId, runLineList, sportRange, pointIdList, okPointListJson, schoolCode, isPublic=isPublic)


async def startSpider(accountId: int,
                      progress_callback: Optional[Callable[[dict], None]] = None) -> None:
    def _emit(phase: str, **kw):
        if progress_callback is None:
            return
        try:
            progress_callback({"phase": phase, **kw})
        except Exception:  # noqa: BLE001
            logger.warning("progress_callback raised; ignored")

    tsnClient: TiShiNengPrivate | TiShiNengSdkPublic | None = None
    async for newDb in get_db():
        tsnClient = await getTsnClientById(accountId, newDb)

    _emit("preparing", msg="加载账号客户端...")

    if tsnClient.isPublic():
        baseRecord = await tsnClient.listExerciseRecord(1, '', 1)
        dates = baseRecord['dates']
        total_records_seen = 0
        for date in dates:
            recodeIdList = []
            for pageIndex in range(1, 10):
                recodeList = await tsnClient.listExerciseRecord(1, date['date'], pageIndex)
                # logger.info(recodeList)
                breakFlag = False
                for i in recodeList['records']:
                    if i['id'] in recodeIdList:
                        breakFlag = True
                        break
                    else:
                        recodeIdList.append(i['id'])
                if breakFlag:
                    break
            logger.info(recodeIdList)
            for i in recodeIdList:
                rawRecord = await tsnClient.getExerciseRecord(i)
                if rawRecord['sportType'] != '0' and int(rawRecord['step']) >= 500:
                    logger.info(f" {tsnClient.schoolCode} {rawRecord}")
                    await processRawAndAddDateBase(tsnClient.schoolCode, rawRecord)
                    total_records_seen += 1
                    _emit("crawling", current=total_records_seen)
    else:
        recodeIdList = []
        for pageIndex in range(1, 10):
            resp = await tsnClient.appSportRecordList(2, pageIndex, 10)
            # logger.info(resp)
            if 'data' not in resp or not resp['data']:
                break
            breakFlag = False
            for data in resp['data']:
                if data['sportStatus'] != 1:
                    continue
                if data['id'] in recodeIdList:
                    breakFlag = True
                    break
                else:
                    recodeIdList.append(data['id'])
            if breakFlag:
                break
        for idx, i in enumerate(recodeIdList, 1):
            rawRecord = await tsnClient.getSportRecordId(i)
            if int(rawRecord['sportStatus']) == 1 and sum(rawRecord['stepNumbers']) >= 500:
                await processRawAndAddDateBase(tsnClient.schoolCode, rawRecord, isPublic=False)
                _emit("crawling", current=idx, total=len(recodeIdList))

    _emit("done")
