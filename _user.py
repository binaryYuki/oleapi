from typing import Dict, Optional
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.orm import Session
from sqlalchemy import select
from starlette.requests import Request

from _db import SessionLocal, User, UserWatchHistory # import UserWatchHistory table

# Create an APIRouter instance for user watch history related endpoints
watch_history_router = APIRouter(prefix='/api/user', tags=['User', 'Watch History'])

# OpenIdConnect configuration
app = FastAPI()
app.include_router(watch_history_router)

# Router for user-related endpoints
userRoute = APIRouter(prefix='/api/user', tags=['User', 'User Management', 'oauth2'])


dbSession = SessionLocal()

# 获取数据库会话
def get_db():
    try:
        yield dbSession
    finally:
        dbSession.close()

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


@watch_history_router.post('/record_watch_history', dependencies = [Depends(RateLimiter(times = 5, seconds = 60))])
async def record_watch_history(request: Request, db: Session = Depends(get_db)):
    """
    记录用户观看历史的接口。
    接收用户 ID 和视频 ID, 将其存储在 UserWatchHistory 表中。
    """
    session_info = get_session_info(request)
    if not session_info:
        return JSONResponse(content={'error': 'Not logged in'}, status_code=401)

    data = await request.json()
    user_id = session_info['user_id']
    video_id = data.get('video_id')

    if not video_id:
        raise HTTPException(status_code=400, detail="Video ID is required")

    new_history = UserWatchHistory(user_id=user_id, vod_id=video_id)

    db.add(new_history)
    db.commit()
    return JSONResponse(content={"message": "Watch history recorded"}, status_code=201)


@watch_history_router.get('/get_watch_history', dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def get_watch_history(request: Request, db: Session = Depends(get_db)):
    """
    获取用户观看历史的接口。
    根据用户 ID 查询 UserWatchHistory 表，并返回该用户的观看记录。
    """
    session_info = get_session_info(request)
    if not session_info:
        return JSONResponse(content={'error': 'Not logged in'}, status_code=401)

    user_id = session_info['user_id']

    history_records = db.query(UserWatchHistory).filter_by(user_id=user_id).all()

    if not history_records:
        return JSONResponse(content={"message": "No watch history found"}, status_code=404)

    history_list = [record.to_dict() for record in history_records]
    return JSONResponse(content={"watch_history": history_list}, status_code=200)
