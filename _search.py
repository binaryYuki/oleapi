import hashlib
import datetime
import json
import logging
import random
import urllib.parse
import httpx
from fastapi import Depends
from fastapi_limiter.depends import RateLimiter
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi.routing import APIRouter

from _redis import get_key, set_key
from _utils import _getRandomUserAgent, generate_vv_detail

searchRouter = APIRouter(prefix='/api/query/ole', tags=['Search', 'Search Api'])


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
    vv = await generate_vv_detail()
    # 关键词是个中文字符串，需要进行 URL 编码
    keyword = url_encode(keyword)
    base_url = f"https://api.olelive.com/v1/pub/index/search/{keyword}/vod/0/{page}/{size}?_vv={str(vv)}"
    logging.info(base_url)
    headers = {
        'User-Agent': _getRandomUserAgent(),
        'Referer': 'https://www.olevod.com/',
        'Origin': 'https://www.olevod.com/',
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, headers=headers)
    if response.status_code != 200:
        return JSONResponse(content={"error": "Upstream Error"}, status_code=501)
    return response.json()


async def link_keywords(keyword):
    vv = await generate_vv_detail()
    if type(vv) is bytes:
        vv = vv.decode()
    # 关键词是个中文字符串，需要进行 URL 编码
    keyword_encoded = url_encode(keyword)
    base_url = f"https://api.olelive.com/v1/pub/index/search/keywords/{keyword_encoded}?_vv={vv}"
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
    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, headers=headers)
    if response.status_code != 200:
        return JSONResponse(content={"error": "Upstream Error"}, status_code=501)
    return response.json()


# url 编码关键词
def url_encode(keyword):
    return urllib.parse.quote(keyword.encode())


@searchRouter.api_route('/search', dependencies=[Depends(RateLimiter(times=1, seconds=1))], methods=['POST'], name='search')
async def search(request: Request):
    data = await request.json()
    keyword, page, size = data.get('keyword'), data.get('page'), data.get('size')
    if keyword == '' or keyword == 'your keyword':
        return JSONResponse({}, status_code=200)
    page, size = int(page), int(size)
    result = await search_api(keyword, page, size)
    return JSONResponse(result)


@searchRouter.api_route('/keyword', dependencies=[Depends(RateLimiter(times=1, seconds=1))], methods=['POST'], name='keyword')
async def keyword(request: Request):
    data = await request.json()
    keyword = data.get('keyword')
    if keyword == '' or keyword == 'your keyword':
        return JSONResponse({}, status_code=200)
    try:
        result = await link_keywords(keyword)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=501)
    return JSONResponse(result)


@searchRouter.api_route('/detail', methods=['POST'], name='detail', dependencies=[Depends(RateLimiter(times=1, seconds=3))])
async def detail(request: Request):
    data = await request.json()
    try:
        id = data.get('id')
    except Exception as e:
        return JSONResponse({"error": "Invalid Request, missing param: id"}, status_code=400, headers={"X-Error": str(e)})
    vv = await generate_vv_detail()
    url = f"https://api.olelive.com/v1/pub/vod/detail/{id}/true?_vv={vv}"
    headers = {
        'User-Agent': _getRandomUserAgent(),
        'Referer': 'https://www.olevod.com/',
        'Origin': 'https://www.olevod.com/',
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        response_data = response.json()
        return JSONResponse(response_data, status_code=200)
    except:
        return JSONResponse({"error": "Upstream Error"}, status_code=501)
    # direct play https://player.viloud.tv/embed/play?url=https://www.olevod.com/vod/detail/5f4b3b7b7f3c1d0001b2b3b3&autoplay=1
