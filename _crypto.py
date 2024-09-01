import logging
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.routing import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

cryptoRouter = APIRouter(prefix='/api/crypto', tags=['Crypto', 'Cryptography'])


async def init_crypto():
    if os.path.exists("private.pem"):
        logging.info("Removing old private key")
        os.remove(os.path.join("private.pem"))
    if os.path.exists("public.pem"):
        logging.info("Removing old public key")
        os.remove(os.path.join("public.pem"))

    # Generate a new private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096
    )
    # Serialize the private key
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_key = private_key.public_key()
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open("private.pem", "wb") as f:
        f.write(pem)
    with open("public.pem", "wb") as f:
        f.write(pem_public)
    return True


@cryptoRouter.api_route('/get', methods=['GET'])
async def get_crypto():
    with open("public.pem", "rb") as f:
        public_key = f.read()
    return JSONResponse(content={"status": "success", "public_key": public_key.decode('utf-8')})


# todo: test method, remove it in production
@cryptoRouter.get('/decrypt')
async def decrypt_data(request: Request):
    data = await request.json()
    data = data.get("data")
    with open("private.pem", "rb") as f:
        private_key = f.read()
    # Decrypt the data
    private_key = serialization.load_pem_private_key(private_key, password=None)
    decrypted_data = private_key.decrypt(data)
    return JSONResponse(content={"status": "success", "decrypted_data": decrypted_data.decode('utf-8')})
