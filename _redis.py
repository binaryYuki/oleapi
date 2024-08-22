import os
from redis import asyncio as redis
from typing import Optional
import dotenv

dotenv.load_dotenv()

# Configuration
if os.getenv("REDIS_CONN") is not None:
    REDIS_CONN = os.getenv("REDIS_CONN")
else:
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    # 在集群环境下，使用 redis:// 连接字符串 并且 tcp()包裹
    REDIS_CONN = f"redis://default:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"


# Initialize Redis client
redis_client = redis.from_url(REDIS_CONN)


async def test_redis():
    try:
        await redis_client.ping()
        return True
    except redis.RedisError as e:
        print(f"Error connecting to Redis: {e}")
        return False


# Set a key-value pair in Redis
async def set_key(key: str, value: str, ex: Optional[int] = None) -> bool:
    """
    Set a value in Redis with an optional expiration time (in seconds).
    """
    try:
        await redis_client.set(name=key, value=value, ex=ex)
        return True
    except redis.RedisError as e:
        print(f"Error setting key in Redis: {e}")
        return False


# Get a value from Redis by key
async def get_key(key: str) -> Optional[str]:
    """
    Get a value from Redis by key. Returns None if the key does not exist.
    """
    try:
        value = await redis_client.get(name=key)
        return value
    except redis.RedisError as e:
        print(f"Error getting key from Redis: {e}")
        return None


# Delete a key from Redis
async def delete_key(key: str) -> bool:
    """
    Delete a key from Redis.
    """
    try:
        await redis_client.delete(key)
        return True
    except redis.RedisError as e:
        print(f"Error deleting key from Redis: {e}")
        return False


# Check if a key exists in Redis
async def key_exists(key: str) -> bool:
    """
    Check if a key exists in Redis.
    """
    try:
        return redis_client.exists(key) == 1
    except redis.RedisError as e:
        print(f"Error checking key in Redis: {e}")
        return False
