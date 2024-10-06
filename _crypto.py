from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Request, Response
from fastapi.routing import APIRouter

from _redis import delete_key as redis_delete_key, get_key as redis_get_key, set_key as redis_set_key

cryptoRouter = APIRouter(prefix='/api/crypto', tags=['Crypto', 'Crypto Api'])


async def init_crypto():
    """
    初始化加密模块
    :return:
    """
    try:
        a = await redis_get_key("private_key")
        b = await redis_get_key("public_key")
        if a and b:
            return True
        else:
            try:
                await redis_delete_key("private_key")
                await redis_delete_key("public_key")
            except Exception as e:
                pass
            # 生成一对rsa密钥 并且保存到redis
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            public_key = private_key.public_key()
            # 保存到redis
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            await redis_set_key("private_key", private_pem.decode())
            await redis_set_key("public_key", public_pem.decode())

            return True
    except Exception as e:
        raise Exception(f"Failed to init crypto: {e}")


@cryptoRouter.options('/getPublicKey')
async def get_public_key(request: Request):
    """
    获取公钥
    :param request:
    :return:
    """
    public_key = await redis_get_key("public_key")
    return Response(content=public_key, media_type="text/plain")
