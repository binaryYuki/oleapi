import binascii
import json
import logging
import os
import random
import subprocess
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_utils.tasks import repeat_every
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse

from _auth import authRoute
from _cronjobs import pushTaskExecQueue
from _crypto import cryptoRouter, init_crypto
from _db import init_db, test_db_connection
from _redis import redis_client, set_key as redis_set_key
from _search import searchRouter
from _trend import trendingRoute
from _user import userRoute

load_dotenv()
loglevel = os.getenv("LOG_LEVEL", "ERROR")
logging.basicConfig(level=logging.getLevelName(loglevel))
logger = logging.getLogger(__name__)


@repeat_every(seconds=60 * 60, wait_first=True)
async def testPushServer():
    async with httpx.AsyncClient() as client:
        f = await client.get("https://push.tzpro.xyz/healthz")
        if f.status_code == 200:
            await redis_set_key("server_status", "running")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    整个 FastAPI 生命周期的上下文管理器
    :param _: FastAPI 实例
    :return: None
    :param _:
    :return:
    """
    redis_connection = redis.from_url(
        f"redis://default:{os.getenv('REDIS_PASSWORD', '')}@{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}")
    await FastAPILimiter.init(redis_connection)
    test = await redis_connection.ping()
    if test:
        logger.info("Redis connection established")
    logger.info("cleaning up redis db")
    await redis_connection.flushdb()
    if os.getenv("MYSQL_CONN_STRING"):
        await init_db()
        logger.info("MySQL connection established")
    await init_crypto()
    await testPushServer()
    await pushTaskExecQueue()
    yield
    await FastAPILimiter.close()
    await redis_client.connection_pool.disconnect()


# 禁用 openapi.json
app = FastAPI(lifespan=lifespan, title="Anime API", version="1.0.0.beta", openapi_url=None)

app.include_router(authRoute)
app.include_router(userRoute)
app.include_router(searchRouter)
app.include_router(trendingRoute)
app.include_router(cryptoRouter)


@app.get('/')
async def index():
    """
    首页
    :return:
    """
    version_suffix = os.getenv("COMMIT_ID", "")[:8]
    info = {
        "version": "v1.0.0-" + version_suffix,
        "build_at": os.environ.get("BUILD_AT", ""),
        "author": "binaryYuki <noreply.tzpro.xyz>",
        "arch": subprocess.run(['uname', '-m'], stdout=subprocess.PIPE).stdout.decode().strip(),
        "commit": os.getenv("COMMIT_ID", ""),
    }

    # 将字典转换为 JSON 字符串并格式化
    json_data = json.dumps(info, indent=4)

    # 将 JSON 数据嵌入到 HTML 页面中
    html_content = f"""
            <pre>{json_data}</pre>
    """

    return HTMLResponse(content=html_content)


@app.api_route('/healthz', methods=['GET'])
async def healthz():
    """
    健康检查
    :return:
    """
    try:
        await redis_client.ping()
        redisStatus = True
    except Exception as e:
        redisHint = str(e)
        redisStatus = False
    # check mysql connection
    try:
        await test_db_connection()
        mysqlStatus = True
    except ConnectionError as e:
        mysqlStatus = False
        mysqlHint = str(e)
    except Exception as e:
        mysqlStatus = False
        mysqlHint = str(e)
    if redisStatus and mysqlStatus:
        return JSONResponse(content={"status": "ok", "redis": redisStatus, "mysql": mysqlStatus})
    else:
        return JSONResponse(content={"status": "error", "redis": redisStatus, "mysql": mysqlStatus,
                                     "redis_hint": redisHint if not redisStatus else "",
                                     "mysql_hint": mysqlHint if not mysqlStatus else ""})

secret_key = os.environ.get("SESSION_SECRET")
if not secret_key:
    secret_key = binascii.hexlify(random.randbytes(16)).decode('utf-8')

# noinspection PyTypeChecker
app.add_middleware(SessionMiddleware, secret_key=secret_key,
                   session_cookie='session', max_age=60 * 60 * 12, same_site='lax', https_only=True)
# noinspection PyTypeChecker
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['*'])
# noinspection PyTypeChecker
app.add_middleware(GZipMiddleware, minimum_size=1000)
if os.getenv("DEBUG", "false").lower() == "false":
    # noinspection PyTypeChecker
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r'^https?:\/\/(localhost:3000|.*\.tzpro\.xyz|.*\.tzpro\.uk)(\/.*)?$',
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'OPTIONS'],  # options 请求是预检请求，需要单独处理
        allow_headers=['Authorization', 'Content-Type', 'Accept', 'Accept-Encoding', 'Accept-Language', 'Origin',
                       'Referer', 'Cookie', 'User-Agent'],
    )
else:
    # noinspection PyTypeChecker
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'OPTIONS'],  # options 请求是预检请求，需要单独处理
        allow_headers=['*']
    )

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8000)
