import datetime
import json
import logging
from logging import getLogger

import dotenv
from fastapi import APIRouter, BackgroundTasks, Request
from sqlalchemy import text
from starlette.responses import JSONResponse

from _db import SessionLocal, User, WebHookStorage

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

dotenv.load_dotenv()

authRoute = APIRouter(prefix='/api/auth', tags=['Auth', 'Authentication'])


async def eventVerifier(event: str):
    """
    Verifies the event received from the webhook
    :param event:
    :return: Boolean
    """
    allowedEvent = ['PostRegister', 'PostResetPassword', 'PostSignIn']
    if event in allowedEvent:
        return True
    return False


async def timeFrameVerifier(timeStamp: str):
    """
    Verifies the time frame received from the webhook
    :param timeStamp: str (time frame)
    :return: Boolean
    """
    try:
        if (datetime.datetime.strptime(timeStamp, '%Y-%m-%dT%H:%M:%S.%fZ') >
                datetime.datetime.now() - datetime.timedelta(minutes=1)):
            return True
        else:
            return False
    except ValueError:
        return False


async def store_webhook_data(data: dict):
    async with SessionLocal() as session:
        async with session.begin():
            webhook = WebHookStorage(
                hook_id=data["hookId"],
                event=data["event"],
                session_id=data["sessionId"],
                user_agent=data["userAgent"],
                user_ip=data["userIp"],
                sessionId=data["sessionId"],
            )
            data = data['user']
            user = User(
                id=data['id'],
                username=data['username'],
                primaryEmail=data['primaryEmail'],
                primaryPhone=data['primaryPhone'],
                name=data['name'],
                avatar=data['avatar'],
                customData=json.dumps(data['customData']),  # 将字典序列化为JSON字符串
                identities=json.dumps(data['identities']),
                profile=json.dumps(data['profile']),
                applicationId=data['applicationId'],
                lastSignInAt=data['lastSignInAt'] / 1000,
                createdAt=data['createdAt'] / 1000,
                updatedAt=data['updatedAt'] / 1000,
            )
            # 通过 id 判断用户是否存在 如果存在就更新用户信息 否则插入新用户
            user_exist = await session.execute(text(f"SELECT * FROM users WHERE id='{data['id']}'"))
            user_exist = user_exist.fetchone()
            if user_exist:
                await session.execute(
                    text(f"UPDATE users SET username='{data['username']}', primaryEmail='{data['primaryEmail']}', "
                         f"primaryPhone='{data['primaryPhone']}', name='{data['name']}', avatar='{data['avatar']}', "
                         f"customData='{json.dumps(data['customData'])}', identities='{json.dumps(data['identities'])}', "
                         f"profile='{json.dumps(data['profile'])}', applicationId='{data['applicationId']}', "
                         f"lastSignInAt='{data['lastSignInAt'] / 1000}', createdAt='{data['createdAt'] / 1000}', "
                         f"updatedAt='{data['updatedAt'] / 1000}' WHERE id='{data['id']}'"))
            else:
                session.add(user)
            session.add(webhook)
            await session.commit()
            await session.close()


@authRoute.api_route('/hook', methods=['POST', 'PUT'])
async def logtoEventHandler(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except Exception as e:
        logger.debug(e)
        return JSONResponse(status_code=401, content={'error': 'Invalid request'})
    if not await eventVerifier(data.get('event')) or not await timeFrameVerifier(data.get('createdAt')):
        return JSONResponse(status_code=401, content={'error': 'Invalid request', 'step': 2})
    background_tasks.add_task(store_webhook_data, data)
    return JSONResponse(status_code=200, content={'message': 'Webhook received successfully'})
