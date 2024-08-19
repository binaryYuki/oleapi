import hashlib
import datetime
import logging
import random
import urllib.parse
import httpx
import requests
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi.routing import APIRouter

from _utils import _getRandomUserAgent, generate_vv_detail

searchRouter = APIRouter(prefix='/api/query', tags=['Search', 'Search Api'])


async def _getProxy():
    return None  # 废弃接口，直接返回 None


async def search_api(keyword, page=1, size=4):
    """
    搜索 API
    :param keyword:  搜索关键词
    :param page:  页码
    :param size:  每页数量
    :return:  返回搜索结果
    """
    vv = generate_vv_detail()
    # 关键词是个中文字符串，需要进行 URL 编码
    keyword = url_encode(keyword)
    base_url = f"https://api.olelive.com/v1/pub/index/search/{keyword}/vod/0/{page}/{size}?_vv={vv}"
    logging.info(base_url, stack_info=True)
    headers = {
        'User-Agent': _getRandomUserAgent(),
        'Referer': 'https://www.olevod.com/',
        'Origin': 'https://www.olevod.com/',
    }
    response = requests.get(base_url, headers=headers)
    if response.status_code != 200:
        return JSONResponse(content={"error": "Upstream Error"}, status_code=501)
    return response.json()


async def link_keywords(keyword):
    vv = generate_vv_detail()
    # 关键词是个中文字符串，需要进行 URL 编码
    keyword_encoded = url_encode(keyword)
    base_url = f"https://api.olelive.com/v1/pub/index/search/keywords/{keyword_encoded}?_vv={vv}"
    logging.info(base_url, stack_info=True)
    headers = {
        'User-Agent': _getRandomUserAgent(),
        'Referer': 'https://www.olevod.com/',
        'Origin': 'https://www.olevod.com/',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
    }
    response = requests.get(base_url, headers=headers)
    if response.status_code != 200:
        return JSONResponse(content={"error": "Upstream Error"}, status_code=501)
    return response.json()


# url 编码关键词
def url_encode(keyword):
    return urllib.parse.quote(keyword.encode())


@searchRouter.post('/search')
async def search(request: Request):
    data = await request.json()
    keyword, page, size = data.get('keyword'), data.get('page'), data.get('size')
    page, size = int(page), int(size)
    result = await search_api(keyword, page, size)
    return JSONResponse(result)


@searchRouter.post('/keyword')
async def keyword(request: Request):
    data = await request.json()
    keyword = data.get('keyword')
    try:
        result = await link_keywords(keyword)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=501)
    return JSONResponse(result)


# 测试
if __name__ == '__main__':
    import asyncio

    # 搜索 "复仇者联盟" 的结果
    result = asyncio.run(search_api("复仇者联盟"))
    print(result)
    result = asyncio.run(link_keywords("复仇者"))
    print(result)
