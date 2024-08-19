from typing import Optional
import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi.routing import APIRouter
from _utils import _getRandomUserAgent, generate_vv_detail as gen_vv

trendingRoute = APIRouter(prefix='/api/trending', tags=['Trending'])


async def gen_url(typeID: int, period: str, amount=10):
    """
    传入的值必须经过检查，否则可能会导致 API 请求失败。
    """
    if period not in ['day', 'week', 'month', 'all']:
        return JSONResponse(status_code=400, content={'error': 'Invalid period parameter, must be one of: day, week, month, all'})
    if typeID not in [1, 2, 3, 4]:
        return JSONResponse(status_code=400, content={'error': 'Invalid typeID parameter, must be one of: 1 --> 电影, 2 --> 电视剧（连续剧）, 3 --> 综艺, 4 --> 动漫'})
    vv = gen_vv()
    url = f"https://api.olelive.com/v1/pub/index/vod/data/rank/{period}/{typeID}/{amount}?_vv={vv}"
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
    data = await request.json()
    typeID, amount = data.get('typeID'), data.get('amount', 10)
    if period is None:
        return JSONResponse(status_code=400, content={'error': 'Missing required parameters: period'})
    if typeID is None:
        return JSONResponse(status_code=400, content={'error': 'Missing required parameters: typeID'})
    if period not in ['day', 'week', 'month', 'all']:
        return JSONResponse(status_code=400, content={'error': 'Invalid period parameter, must be one of: day, week, month, all'})
    if typeID not in [1, 2, 3, 4]:
        return JSONResponse(status_code=400, content={'error': 'Invalid typeID parameter, must be one of: 1 --> 电影, 2 --> 电视剧（连续剧）, 3 --> 综艺, 4 --> 动漫'})
    url = await gen_url(typeID, period, amount)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={'User-Agent': _getRandomUserAgent()}, timeout=30)
            data = response.json()
            return JSONResponse(status_code=200, content=data)
    except httpx.RequestError as e:
        print(data)
        return JSONResponse(status_code=response.status_code if response.status_code else 500, content={'error': f"An error occurred: {e}"})
    except httpx.HTTPStatusError as e:
        print(data)
        return JSONResponse(status_code=response.status_code if response.status_code else 500, content={'error': f"An HTTP error occurred: {e}"})
    except Exception as e:
        print(data)
        return JSONResponse(status_code=response.status_code if response.status_code else 500, content={'error': f"An error occurred: {e}, response: {response.text}"})


