from fastapi import APIRouter, FastAPI

from _db import SessionLocal

app = FastAPI()

# OpenIdConnect configuration

# Router for user-related endpoints
userRoute = APIRouter(prefix='/api/user', tags=['User', 'User Management', 'oauth2'])

dbSession = SessionLocal()
