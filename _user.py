from typing import Dict, Optional

from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import RedirectResponse

from _db import SessionLocal, User

app = FastAPI()

# OpenIdConnect configuration

# Router for user-related endpoints
userRoute = APIRouter(prefix='/api/user', tags=['User', 'User Management', 'oauth2'])

dbSession = SessionLocal()


def get_session_info(request: Request) -> Optional[Dict]:
    """
    Extract and return session information from the request.
    从请求中提取并返回会话信息。
    """
    session = request.session

    if not session:
        return None

    # Parse and return relevant session info
    session_info = {
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'email_verified': session.get('email_verified'),
        'oidc_access_token': session.get('oidc_access_token'),
    }

    return session_info


@userRoute.api_route('/profile', dependencies=[Depends(RateLimiter(times=1, seconds=1))], methods=['POST'])
async def get_user_profile(request: Request):
    """
    Get the user's profile information.
    用户信息获取接口
    """
    db: SessionLocal = SessionLocal()
    session_info = get_session_info(request)
    if not session_info:
        return JSONResponse(content={'error': 'Not logged in'}, status_code=401)

    user = await db.execute(
        select(User).filter(User.user_id == session_info['user_id'])
    )
    user = user.scalars().first()
    if not user:
        del request.cookies['session']
        return JSONResponse(content={'error': 'User not found'}, status_code=404)
    else:
        return JSONResponse(content=user.to_dict(), status_code=200)


@userRoute.api_route('/update', dependencies=[Depends(RateLimiter(times=1, seconds=20))], methods=['POST'])
async def update_user_profile(request: Request):
    """
    Update the user's profile information.
    用户信息更新接口
    允许的字段：username, email, avatar
    ！要求带上 session
    """
    allwoed_keys = ['username', 'avatar', 'email_verified', 'sub_limit', 'bark_token']
    session_info = get_session_info(request)
    if not session_info:
        return JSONResponse(content={'error': 'Not logged in'}, status_code=401)
    data = await request.json()
    user_id = session_info['user_id']
    db: SessionLocal = SessionLocal()
    user = await db.execute(
        select(User).filter(User.user_id == user_id)
    )
    user = user.scalars().first()
    if not user:
        del request.cookies['session']
        return JSONResponse(content={"success": False, "message": "User not found"}, status_code=404)
    for key in data.keys():
        if key in allwoed_keys:
            setattr(user, key, data[key])
    db.commit()
    return JSONResponse(content={"success": True}, status_code=201)


@userRoute.api_route('/subscribe', dependencies=[Depends(RateLimiter(times=1, seconds=1))], methods=['POST'])
async def subscribe(request: Request):
    """
    Subscribe to a user.
    订阅用户

    """
    user_id = request.session.get('user_id')
    if not user_id or not request.session:
        response = RedirectResponse(url='/api/auth/login', status_code=302)
        response.delete_cookie('session')
        return response
    if not request.json():
        return JSONResponse(content={'error': 'Invalid request'}, status_code=400)
    data = await request.json()
