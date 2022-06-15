import asyncio
import json
import pathlib
from typing import List

import aiohttp
from pydantic import BaseModel
from aiofile import async_open
from aiohttp.client_exceptions import InvalidURL

DataPath = pathlib.Path("data")


class Skins(BaseModel):
    """皮肤模型
    """
    name: str
    mainImg: str
    chromaImg: str


class Info(BaseModel):
    """信息模型
    """
    name: str
    title: str
    shortBio: str


class Hero(BaseModel):
    """英雄模型
    """
    hero: Info
    skins: List[Skins]


class Link(BaseModel):
    heroId: int
    name: str


class HeroInfo(BaseModel):
    hero: List[Link]


async def request_api(session, url, params):
    """信息api请求
    :param session: session
    :param url: 链接
    :param params: 参数
    :return:
    """
    async with session.get(url, params=params) as response:
        return await response.text()


async def parse(data):
    """解析api数据
    :param data:
    :return:
    """
    return Hero(**json.loads(data))


async def save_skins(session, hero: Hero, skin: Skins):
    """保存皮肤封面
    :param session:
    :param hero:
    :param skin:
    :return:
    """
    url = skin.mainImg
    if not url:
        return
    try:
        async with session.get(url) as res:
            await save_image(hero, skin, res)
    except InvalidURL:
        pass


async def download_skins(session, hero: Hero):
    """并发下载该英雄的所有皮肤
    :param session:
    :param hero:
    :return:
    """
    await asyncio.gather(*[save_skins(session, hero, skin) for skin in hero.skins])


async def save_image(hero: Hero, skin: Skins, response):
    """保存图片
    :param hero:
    :param skin:
    :param response: response 对象
    :return:
    """
    path = DataPath / hero.hero.name / (skin.name + ".jpg")
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    print("save %s 的 %s 皮肤 到 %s" % (hero.hero.name, skin.name, path))
    async with async_open(path, "wb") as fp:
        await fp.write(
            await response.read()
        )


async def save_json(hero: Hero):
    """保存英雄信息
    :param hero:
    :return:
    """
    print("save", hero.hero.name)
    path = DataPath / hero.hero.name / (hero.hero.name + ".json")
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    async with async_open(path, "w") as fp:
        await fp.write(hero.json(ensure_ascii=False, indent=2))


async def wrapper(session, item):
    hero = await parse(item)
    await save_json(hero)
    await download_skins(session, hero)


async def main():
    """主函数
    """
    hero_list_url = "https://game.gtimg.cn/images/lol/act/img/js/heroList/hero_list.js?ts=2758790"
    url = "https://game.gtimg.cn/images/lol/act/img/js/hero/%d.js"
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/102.0.5005.115 Safari/537.36"}
    conn = aiohttp.TCPConnector(limit=15)
    async with aiohttp.ClientSession(connector=conn, headers=headers) as session:
        # 并发请求所有信息
        text = await request_api(session, hero_list_url, params=None)
        hero_list = await parse_hero(text)
        hero_ids = (hero_info.heroId for hero_info in hero_list.hero)
        tasks = [request_api(session, url % i, params={"ts": 2758522}) for i in hero_ids]
        data = await asyncio.gather(*tasks)
        await asyncio.gather(*[wrapper(session, item) for item in data])


async def parse_hero(text) -> HeroInfo:
    return HeroInfo.parse_raw(text)


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
