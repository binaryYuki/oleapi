import logging
import os
import random
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from _db import testSQL
from _redis import get_key, redis_client, set_key
from _trend import trendingRoute
from _user import userRoute
from _auth import authRoute
from _search import searchRouter
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

load_dotenv()

logging.getLogger().setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    redis_connection = redis.from_url(
        f"redis://default:{os.getenv('REDIS_PASSWORD', '')}@{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}")
    await FastAPILimiter.init(redis_connection)
    test = await redis_connection.ping()
    if test:
        logging.info("Redis connection established")
    if os.getenv("MYSQL_CONN_STRING"):
        await testSQL()
        logging.info("MySQL connection established")
    yield
    await FastAPILimiter.close()
    await redis_client.connection_pool.disconnect()

# 禁用 openapi.json
app = FastAPI(lifespan=lifespan, title="Anime API", version="0.1.5.beta-1-g80713e6", openapi_url=None)

app.include_router(authRoute)
app.include_router(userRoute)
app.include_router(searchRouter)
app.include_router(trendingRoute)


@app.get('/')
async def index():
    info = {
        "version": "v0.1.5.beta-1-g80713e6",
        "build": "2024-08-19 11:03:45",
        "author": "binaryYuki <noreply.tzpro.xyz>",
        "arch": os.system('uname -m'),
        "commit": "80713e6bc52146d1b9af109bab8d9e008679f5c9",
    }
    return JSONResponse(content=info)


@app.get('/getsession', dependencies=[Depends(RateLimiter(times=1, seconds=10))])
async def get_session(request: Request):
    if request.session == {}:
        return JSONResponse(content={'session': 'None'}, status_code=401)
    return JSONResponse(content={'session': request.session})


@app.get('/test', dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def test(request: Request):
    """
    测试接口 返回用户的 session 信息
    限速 1 次/秒
    :param request:  请求对象
    :return:  返回用户的 session 信息/html 页面 要求登录
    """
    # 返回用户的 session 等原始请求信息 包含 cookie
    if request.session == {} and request.cookies == {}:
        # 一个按钮 跳转到 /api/auth/login
        html_content = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>Test</title>
        </head>
        <body>
            <h3>还没有登录</h3>
            <h4>该接口仅供测试</h4>
            <h5>点击下方按钮登录</h5>
            <a href="/api/auth/login">Login</a>
        </body>
        </html>
        """
        return Response(content=html_content, media_type="text/html")
    elif request.session == {} and request.cookies != {}:
        response = RedirectResponse(url='/test')
        response.delete_cookie('session')
        return response
    return JSONResponse(content={'session': request.session, 'cookies': request.cookies})


app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", random.randbytes),
                   session_cookie='session', max_age=60 * 60 * 12)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['*'])
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['GET', 'POST'],
                   allow_headers=[
                       'Authorization, Content-Type, Origin, X-Requested-With, Accept, Accept-Encoding, Accept-Language, Host, Referer, User-Agent',
                       'Set-Cookie']),  # 允许跨域请求

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='localhost', port=8000)
