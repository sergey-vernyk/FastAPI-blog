from asgiref.sync import async_to_sync
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aredis

from celery_app import app
from settings.env_dirs import REDIS_CACHE_URL


@app.task(name='invalidate_cache')
def invalidate_endpoint_cache(namespace: str, request_method: str) -> str:
    """
    Task removes keys from redis cache when there was request on update,
    create or delete data in database.
    * namespace - name of table in database.
      This name used as part of cache key, where cache is located.
      And next request to the table will be performed instead of getting data from cache.
    * request_method - means method when next request will be accomplished without using cache.

    Key in the cache may be looks like:
    "posts:get:/api/v1/posts/read_all/posts:'(limit,100),(skip,0),(sort_by,created_desc)'"

    namespace - `post`
    method - `get`
    request path - `/api/v1/posts/read_all/posts`
    query params - `(limit,100),(skip,0),(sort_by,created_desc)`
    """
    if delete_keys_redis(namespace, request_method):
        return f'Cache in `{namespace}` namespace has been invalidated.'
    return f'Cache in namespace `{namespace}` is already empty.'


@async_to_sync
async def delete_keys_redis(namespace: str, request_method: str) -> int:
    """
    Returns number of removed keys from redis cache.
    """
    redis = aredis.from_url(REDIS_CACHE_URL)
    backend = RedisBackend(redis)
    # find keys using pattern with `*`
    # for example: `posts:get:`, `users:get:` will be found
    key_for_delete = await redis.keys(f'{namespace}:{request_method}:*')
    count = 0
    for key in key_for_delete:
        await backend.clear(key=key)
        count += 1
    # don't forget to close client connection,
    # to avoid error `RuntimeError('Event loop is closed')`
    await redis.aclose()
    return count
