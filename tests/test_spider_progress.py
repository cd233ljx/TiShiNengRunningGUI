"""startSpider 进度回调契约测试。"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import spiderServer


@pytest.mark.asyncio
async def test_start_spider_no_callback_still_works():
    """不传 callback 时行为不变（兼容 CLI 调用）。"""
    fake_client = MagicMock()
    fake_client.isPublic.return_value = False
    fake_client.schoolCode = "T"
    fake_client.appSportRecordList = AsyncMock(return_value={"data": []})

    async def fake_get_db():
        yield MagicMock()

    with patch("spiderServer.getTsnClientById", AsyncMock(return_value=fake_client)), \
         patch("spiderServer.get_db", fake_get_db):
        # 不抛异常即通过
        await spiderServer.startSpider(accountId=1)


@pytest.mark.asyncio
async def test_start_spider_emits_progress_when_callback_given():
    """传 callback 时，应在抓到记录后 emit 至少一次 'crawling' 事件。"""
    cb = MagicMock()
    fake_client = MagicMock()
    fake_client.isPublic.return_value = False
    fake_client.schoolCode = "T"
    # 第一页一条 sportStatus==1 的记录；第二页空 → 跳出
    fake_client.appSportRecordList = AsyncMock(side_effect=[
        {"data": [{"id": "rec-1", "sportStatus": 1}]},
        {"data": []},
    ])
    fake_client.getSportRecordId = AsyncMock(return_value={
        "sportStatus": 1, "stepNumbers": [600], "id": "rec-1",
    })

    async def fake_get_db():
        yield MagicMock()

    with patch("spiderServer.getTsnClientById", AsyncMock(return_value=fake_client)), \
         patch("spiderServer.get_db", fake_get_db), \
         patch("spiderServer.processRawAndAddDateBase", AsyncMock(return_value=None)):
        await spiderServer.startSpider(accountId=1, progress_callback=cb)

    phases = [c.args[0]["phase"] for c in cb.call_args_list]
    assert "crawling" in phases, f"phases={phases}"
