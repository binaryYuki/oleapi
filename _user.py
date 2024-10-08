from fastapi import APIRouter, FastAPI

app = FastAPI()

# OpenIdConnect configuration

# Router for user-related endpoints
userRoute = APIRouter(prefix='/api/user', tags=['User', 'User Management', 'oauth2'])
