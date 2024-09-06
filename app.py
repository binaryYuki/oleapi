import json
import logging
import os
import random
import subprocess
from contextlib import asynccontextmanager

import binascii
import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse

from _auth import authRoute
from _crypto import cryptoRouter, init_crypto
from _db import init_db, test_db_connection
from _redis import redis_client
from _search import searchRouter
from _trend import trendingRoute
from _user import userRoute

load_dotenv()

logging.getLogger().setLevel(logging.ERROR)


@asynccontextmanager
async def lifespan(_: FastAPI):
    redis_connection = redis.from_url(
        f"redis://default:{os.getenv('REDIS_PASSWORD', '')}@{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}")
    await FastAPILimiter.init(redis_connection)
    test = await redis_connection.ping()
    if test:
        logging.info("Redis connection established")
    logging.info("cleaning up redis db")
    await redis_connection.flushdb()
    if os.getenv("MYSQL_CONN_STRING"):
        await init_db()
        logging.info("MySQL connection established")
    await init_crypto()
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


@app.get('/getsession', dependencies=[Depends(RateLimiter(times=1, seconds=10))])
async def get_session(request: Request):
    if request.session == {}:
        return JSONResponse(content={'session': 'None'}, status_code=401)
    return JSONResponse(content={'session': request.session})


@app.api_route('/healthz', methods=['GET'])
async def healthz():
    # check redis connection
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

app.add_middleware(SessionMiddleware, secret_key=secret_key,
                       session_cookie='session', max_age=60 * 60 * 12, same_site='lax', https_only=True)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['*'])
app.add_middleware(GZipMiddleware, minimum_size=1000)
if os.getenv("DEBUG", "false").lower() == "false":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['https://anime.tzpro.xyz', 'https://animeapi.tzpro.xyz'],
        allow_credentials=True,
        allow_methods=['GET', 'POST'],
        allow_headers=['*']
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['GET', 'POST'],
        allow_headers=['*']
    )

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8000)
