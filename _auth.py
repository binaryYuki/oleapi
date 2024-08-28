import datetime
import logging
import os
import random
import uuid
from logging import getLogger
from urllib.parse import urlencode

import dotenv
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from _db import SessionLocal, User

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

dotenv.load_dotenv()

authRoute = APIRouter(prefix='/api/auth', tags=['Auth', 'Authentication'])

# Configuration
OIDC_AUTHORIZATION_ENDPOINT = os.environ.get('OIDC_AUTHORIZATION_ENDPOINT')
OIDC_TOKEN_ENDPOINT = os.environ.get('OIDC_TOKEN_ENDPOINT')
OIDC_USERINFO_ENDPOINT = os.environ.get('OIDC_USERINFO_ENDPOINT')
OIDC_SCOPES = os.environ.get('OIDC_SCOPES')
REDIRECT_URI = os.environ.get('REDIRECT_URI')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
user_agent = "TZPro/0.0.1beta (Linux; Ubuntu 20.04)"

# initial baseurl from .env
redirectURL = os.getenv('REDIRECT_PATH', '/test')


# Helper function to generate a random string (for CSRF protection)
def random_string(length: int):
    return random.randbytes(length).hex()


# Endpoint to initiate login
@authRoute.get('/login')
async def login(request: Request):
    try:
        state = request.session['state']
        params = request.query_params
        if 'redirect_url' in params:
            request.session['redirect_url'] = params['redirect_url']
    except KeyError:
        state = random_string(16)
        request.session['state'] = state
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': OIDC_SCOPES,
        'state': state
    }
    auth_url = f"{OIDC_AUTHORIZATION_ENDPOINT}?{urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=307, headers={'Set-Cookie': f'session={request.session}'})


# Endpoint to exchange the authorization code for tokens
async def exchange_code_for_tokens(code: str):
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(OIDC_TOKEN_ENDPOINT, data=payload, headers={'User-Agent': user_agent},
                                         timeout=30)
            response.raise_for_status()  # This raises an exception for 4xx/5xx responses
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to exchange code for tokens: {e}")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()


# Helper function to fetch user info from OIDC provider
async def fetch_userinfo(access_token: str):
    headers = {'Authorization': f'Bearer {access_token}', 'User-Agent': user_agent}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(OIDC_USERINFO_ENDPOINT, headers=headers, timeout=30)
            response.raise_for_status()  # This raises an exception for 4xx/5xx responses
        except Exception as e:
            raise ChildProcessError(f"Failed to fetch userinfo: {e}")
        if response.status_code != 200:
            raise ChildProcessError(f"Failed to fetch userinfo: {response.text}")
        return response.json()


# Route to handle OAuth2 callback
@authRoute.get('/callback')
async def callback(request: Request, code: str, state: str):
    db: SessionLocal = SessionLocal()
    # Verify state for CSRF protection
    if state != request.session.get('state'):
        raise HTTPException(status_code=400, detail='Invalid state')

    # Exchange code for tokens
    tokens = await exchange_code_for_tokens(code)
    userinfo = await fetch_userinfo(tokens['access_token'])
    try:
        user = await get_or_create_user(userinfo)
    except ChildProcessError as e:
        del request.session['state']
        return RedirectResponse(url="/api/auth/login", status_code=307,
                                headers={'Set-Cookie': f'session={request.session}'})
    except Exception as e:
        logging.error(f"Error: {e}")
        raise HTTPException(status_code=400, detail="Failed to authenticate2")

    # Store tokens and user info in session
    request.session['user_id'] = user.user_id
    request.session['user_name'] = user.username
    request.session['email_verified'] = user.email_verified
    request.session['oidc_access_token'] = tokens['access_token']

    User.last_login = str(datetime.datetime.now(datetime.timezone.utc))
    logging.info(f"User {user.username} logged in at {User.last_login}")
    await db.commit()

    if 'redirect' in request.session:
        redirect_URL = request.session['redirect_url']
        del request.session['redirect_url']
        return RedirectResponse(url=str(redirect_URL), headers={'Set-Cookie': f'session={request.session}'},
                                status_code=307)

    # Redirect to the desired page (e.g., home page)
    return RedirectResponse(url=str(os.environ.get("REDIRECT_PATH", request.headers.get("referer", "/"))),
                            headers={'Set-Cookie': f'session={request.session}'}, status_code=307)

    # Function to create or fetch a user based on OIDC userinfo


async def get_or_create_user(userinfo: dict):
    async with SessionLocal() as db:  # Use context manager to ensure proper session handling
        try:
            result = await db.execute(
                select(User).filter(User.oidc_sub == userinfo['sub'])
            )
            user = result.scalars().first()

            if user:
                # Update existing user with new information
                user.name = userinfo.get('name', '')
                user.email = userinfo.get('email', '')
                user.email_verified = userinfo.get('email_verified', False)
                user.avatar = userinfo.get('picture', '')
                user.last_login = datetime.datetime.now(datetime.timezone.utc)  # Update last login time
            else:
                # Create new user
                username = userinfo.get('name', '')
                if not username:
                    username = f"user_{uuid.uuid4().hex[:8]}"
                user = User(
                    user_id=uuid.uuid4().hex,
                    username=username,
                    oidc_sub=userinfo['sub'],
                    avatar=userinfo.get('picture', ''),
                    email=userinfo.get('email', ''),
                    email_verified=userinfo.get('email_verified', False),
                    created_at=datetime.datetime.now(datetime.timezone.utc),  # Set creation time
                    last_login=datetime.datetime.now(datetime.timezone.utc)  # Set last login time
                )
                db.add(user)

            await db.commit()
            await db.refresh(user)
            return user

        except Exception as e:
            await db.rollback()
            print(f"Error: {e}")
            raise e
