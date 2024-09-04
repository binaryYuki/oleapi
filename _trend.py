import logging
from json import JSONDecodeError
from typing import Optional

import httpx
from fastapi import Depends
from fastapi.routing import APIRouter
from fastapi_limiter.depends import RateLimiter
from starlette.requests import Request
from starlette.responses import JSONResponse

from _utils import _getRandomUserAgent, generate_vv_detail as gen_vv

trendingRoute = APIRouter(prefix='/api/trending', tags=['Trending'])


async def gen_url(typeID: int, period: str, amount=10):
    """
    传入的值必须经过检查，否则可能会导致 API 请求失败。
    """
    if period not in ['day', 'week', 'month', 'all']:
        return JSONResponse(status_code=400,
                            content={'error': 'Invalid period parameter, must be one of: day, week, month, all'})
    if typeID not in [1, 2, 3, 4]:
        return JSONResponse(status_code=400, content={
            'error': 'Invalid typeID parameter, must be one of: 1 --> 电影, 2 --> 电视剧（连续剧）, 3 --> 综艺, 4 --> 动漫'})
    vv = await gen_vv()
    url = f"https://api.olelive.com/v1/pub/index/vod/data/rank/{period}/{typeID}/{amount}?_vv={vv}"
    return url


async def gen_url_v2(typeID: int, amount=10):
    """
    传入的值必须经过检查，否则可能会导致 API 请求失败。
    """
    if typeID not in [1, 2, 3, 4]:
        return JSONResponse(status_code=400, content={
            'error': 'Invalid typeID parameter, must be one of: 1 --> 电影, 2 --> 电视剧（连续剧）, 3 --> 综艺, 4 --> 动漫'})
    vv = await gen_vv()
    url = f"https://api.olelive.com/v1/pub/index/vod/hot/{typeID}/0/{amount}?_vv={vv}"
    return url


@trendingRoute.post('/{period}/trend')
async def fetch_trending_data(request: Request, period: Optional[str] = 'day'):
    """
    Fetch trending data from the OLE API.
    :param request: The incoming request.
    :parameter period: The period of time to fetch trending data for. --> str Options: 'day', 'week', 'month', 'all'
    :parameter typeID: The type ID of the item. --> int
    typeID docs:
    1: 电影
    2: 电视剧（连续剧）
    3: 综艺
    4: 动漫
    :parameter amount: The number of items to fetch. --> int default: 10
    """
    try:
        data = await request.json()
        try:
            typeID = data['params']['typeID']
            logging.info(f"typeID1: {typeID}")
        except KeyError as e:
            return JSONResponse(status_code=400, content={'error': f"Where is your param?"})
    except JSONDecodeError as e:
        logging.error(f"JSONDecodeError: {e}, hint: request.json() failed, step fetch_trending_data")
        return JSONResponse(status_code=400, content={'error': f"Where is your param?"})
    if period is None:
        logging.error(f"period: {period}, hint: period is None, step fetch_trending_data")
        return JSONResponse(status_code=400, content={'error': 'Missing required parameters: period'})
    if typeID is None:
        logging.info(f"typeID: {typeID}, hint:typeID is None, step fetch_trending_data")
        return JSONResponse(status_code=400, content={'error': 'Missing required parameters: typeID'})
    if period not in ['day', 'week', 'month', 'all']:
        logging.error(f"period: {period}, hint:period not in ['day', 'week', 'month', 'all]")
        return JSONResponse(status_code=400,
                            content={'error': 'Invalid period parameter, must be one of: day, week, month, all'})
    if typeID not in [1, 2, 3, 4]:
        logging.error(f"typeID: {typeID}, hint:typeID not in [1,2,3,4]")
        return JSONResponse(status_code=400, content={
            'error': 'Invalid typeID parameter, must be one of: 1 --> 电影, 2 --> 电视剧（连续剧）, 3 --> 综艺, 4 --> 动漫'})
    url = await gen_url(typeID, period, amount=10)
    logging.info(f"Fetching trending data from: {url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={'User-Agent': _getRandomUserAgent()}, timeout=30)
            data = response.json()
            return JSONResponse(status_code=200, content=data)
    except httpx.RequestError as e:
        print(data)
        return JSONResponse(status_code=500, content={'error': f"An error occurred: {e}"})
    except httpx.HTTPStatusError as e:
        print(data)
        return JSONResponse(status_code=500, content={'error': f"An HTTP error occurred: {e}"})
    except Exception as e:
        print(data)
        return JSONResponse(status_code=500, content={'error': f"An error occurred: {e}, response: {response.text}"})


@trendingRoute.api_route('/v2/{typeID}', methods=['POST'], dependencies=[Depends(RateLimiter(times=5, seconds=1))])
async def fetch_trending_data_v2(request: Request, typeID: Optional[int] = None):
    """
    Fetch trending data from the OLE API.
    :param request: The incoming request.
    :parameter typeID: The type ID of the item. --> int
    typeID docs:
    1: 电影
    2: 电视剧（连续剧）
    3: 综艺
    4: 动漫
    :parameter amount: The number of items to fetch. --> int default: 10
    """
    try:
        amount = request.query_params['amount']
    except KeyError as e:
        amount = 10
    if typeID is None:
        logging.info(f"typeID: {typeID}, hint:typeID is None, step fetch_trending_data")
        return JSONResponse(status_code=400, content={'error': 'Missing required parameters: typeID'})
    if typeID not in [1, 2, 3, 4]:
        logging.error(f"typeID: {typeID}, hint:typeID not in [1,2,3,4]")
        return JSONResponse(status_code=400, content={
            'error': 'Invalid typeID parameter, must be one of: 1 --> 电影, 2 --> 电视剧（连续剧）, 3 --> 综艺, 4 --> 动漫'})
    url = await gen_url_v2(typeID, amount)
    logging.info(f"Fetching trending data from: {url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={'User-Agent': _getRandomUserAgent()}, timeout=30)
            data = response.json()
            return JSONResponse(status_code=200, content=data)
    except httpx.RequestError as e:
        return JSONResponse(status_code=500, content={'error': f"An error occurred: {e}"})
