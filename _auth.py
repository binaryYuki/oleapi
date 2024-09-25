import datetime
import logging
from logging import getLogger

import dotenv
from fastapi import APIRouter, BackgroundTasks, Request
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
                ip=data["ip"],
                user_ip=data["userIp"],
            )
            session.add(webhook)
            session.commit()


async def process_hook_users(data: dict):
    async with SessionLocal() as session:
        async with session.begin():
            data = data['user']
            user = User(
                id=data['id'],
                username=data['username'],

            )


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
