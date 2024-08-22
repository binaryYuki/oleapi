import os
import random
import uuid
from datetime import datetime

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
import httpx
from urllib.parse import urlencode
from sqlalchemy.exc import NoResultFound
import dotenv
from _db import SessionLocal, User, get_db

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
    state = request.session['state'] = random_string(16)
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': OIDC_SCOPES,
        'state': state
    }
    auth_url = f"{OIDC_AUTHORIZATION_ENDPOINT}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


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
        response = await client.post(OIDC_TOKEN_ENDPOINT, data=payload, headers={'User-Agent': user_agent})
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()


# Helper function to fetch user info from OIDC provider
async def fetch_userinfo(access_token: str):
    headers = {'Authorization': f'Bearer {access_token}', 'User-Agent': user_agent}
    async with httpx.AsyncClient() as client:
        response = await client.get(OIDC_USERINFO_ENDPOINT, headers=headers)
        if response.status_code != 200:
            response = RedirectResponse(url='/api/auth/login', status_code=307, headers={'X-ERROR': 'GRANT EXPIRED'})
            response.delete_cookie('session')
            return response
        return response.json()


# Route to handle OAuth2 callback
@authRoute.get('/callback')
async def callback(request: Request, code: str, state: str, db: SessionLocal = Depends(get_db)):
    # Verify state for CSRF protection
    if state != request.session.get('state'):
        raise HTTPException(status_code=400, detail='Invalid state')

    # Exchange code for tokens
    try:
        tokens = await exchange_code_for_tokens(code)

        # Fetch user info from OIDC provider
        userinfo = await fetch_userinfo(tokens['access_token'])

        # Check if user exists in the database; if not, create a new user
        user = await get_or_create_user(db, userinfo)
    except Exception as e:
        print(e)
        response = RedirectResponse(url='/api/auth/login', status_code=307, headers={'X-ERROR': 'GRANT EXPIRED'})
        response.delete_cookie('session')
        return response

    # Store tokens and user info in session
    request.session['user_id'] = user.user_id
    request.session['user_name'] = user.username
    request.session['access_token'] = tokens['access_token']

    User.last_login = str(datetime.now())
    db.commit()

    # Redirect to the desired page (e.g., home page)
    return RedirectResponse(url=str(redirectURL))


# Function to create or fetch a user based on OIDC userinfo
async def get_or_create_user(db: SessionLocal, userinfo: dict) -> User:
    try:
        user = db.query(User).filter(User.oidc_sub == userinfo['sub']).one()
        user.name = userinfo.get('name', '')
        user.email = userinfo.get('email', '')
        user.email_verified = userinfo.get('email_verified', False)
        user.avatar = userinfo.get('picture', '')
        db.commit()
    except NoResultFound:
        print('Creating new user:', userinfo)
        username = userinfo.get('name', '')
        if username is None or username == '':
            username = f"user_{uuid.uuid4().hex[:8]}"
        user = User(
            user_id=uuid.uuid4().hex,
            username=username,
            oidc_sub=userinfo['sub'],
            avatar=userinfo.get('picture', ''),
            email=userinfo.get('email', ''),
            email_verified=userinfo.get('email_verified', False)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
