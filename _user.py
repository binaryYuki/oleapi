from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import RedirectResponse
from _db import SessionLocal, User, get_db
from fastapi import Depends, FastAPI
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

app = FastAPI()

# OpenIdConnect configuration

# Router for user-related endpoints
userRoute = APIRouter(prefix='/api/user', tags=['User', 'User Management', 'oauth2'])

dbSession = SessionLocal()


@userRoute.get('/profile', dependencies=[Depends(RateLimiter(times=1, seconds=20))])
async def get_user_profile(request: Request):
    """
    Get the user's profile information.
    用户信息获取接口
    注意 email 会经过 base64 编码
    """
    userID = request.session.get('user_id')
    if not userID:
        response = RedirectResponse(url='/api/auth/login', status_code=302)
        response.delete_cookie('session')
        return response
    user = dbSession.query(User).filter(User.user_id == userID).first()
    if not user:
        return JSONResponse(content={'error': 'User not found'}, status_code=404)
    content = user.to_dict()
    content['email'] = content['email'].encode('utf-8').hex()
    return JSONResponse(content=content, status_code=200)


@userRoute.post('/update', dependencies=[Depends(RateLimiter(times=1, seconds=20))])
async def update_user_profile(request: Request):
    """
    Update the user's profile information.
    用户信息更新接口
    允许的字段：username, email, avatar
    ！要求带上 session
    """
    userID = request.session.get('user_id')
    if not userID:
        response = RedirectResponse(url='/api/auth/login', status_code=302)
        response.delete_cookie('session')
        return response
    user = dbSession.query(User).filter(User.user_id == userID).first()
    if not user:
        return JSONResponse(content={'error': 'User not found'}, status_code=404)
    data = await request.json()
    if data['type'] != 'update':
        return JSONResponse(content={'error': 'Invalid request type'}, status_code=400)
    for key, value in data.items():
        setattr(user, key, value)
    allwoed_keys = ['username', 'email', 'avatar']  # 允许修改的字段
    for key in data.keys():
        if key not in allwoed_keys:
            return JSONResponse(content={'error': 'Invalid key'}, status_code=400)
    dbSession.commit()
    return JSONResponse(content=user.to_dict(), status_code=201)
