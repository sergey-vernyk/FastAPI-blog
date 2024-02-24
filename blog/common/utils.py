import codecs
import pickle
from typing import Callable, Any

from fastapi import status, HTTPException, Request
from fastapi_cache.coder import PickleCoder
from starlette.responses import Response


def show_exception(sub: str, error: int) -> HTTPException:
    """
    Returns exception info about `sub` and explanation about `error` type.
    """
    info = {
        status.HTTP_404_NOT_FOUND: f'{sub.capitalize()} with passed id does not exists',
        status.HTTP_403_FORBIDDEN: f'{sub.capitalize()} can be deleted/updated only by staff users or by its owner',
        status.HTTP_400_BAD_REQUEST: f'{sub.capitalize()} already exists'
    }
    return HTTPException(status_code=error, detail=info[error])


def create_cookie(response: Response, key: str, value: str) -> None:
    """
    Create cookie from `key` and `value`.
    """
    response.set_cookie(
        key=key,
        value=value,
        max_age=3600,  # Set the cookie to expire after 3600 seconds (60 minutes)
        httponly=True,  # Ensures that the cookie is only accessible via HTTP (not JavaScript)
        secure=True,  # Ensures that the cookie is only sent over HTTPS
        samesite='strict',  # Prevents the cookie from being sent in cross-site requests
    )


def delete_cookie(response: Response, key: str) -> None:
    """
    Remove cookie from client side by `key`.
    """
    response.delete_cookie(
        key=key,
        secure=True,
        httponly=True,
        samesite='strict'
    )


def base36encode(number: int) -> str:
    """
    Converts an integer to a base36 string.
    Raise ValueError if the input will not fit into an int.
    """

    char_set = '0123456789abcdefghijklmnopqrstuvwxyz'

    if not isinstance(number, int):
        raise TypeError('Number must be an integer')

    if number < 0:
        raise ValueError('Negative base36 conversion input')

    base36 = ''

    if number <= 36:
        return char_set[number]

    while number != 0:
        number, i = divmod(number, len(char_set))
        base36 = char_set[i] + base36

    return base36


def base36decode(b36_string: str) -> int:
    """
    Convert a base36 string `b36string` to an int.
    """
    if len(b36_string) > 13:
        raise ValueError('Base36 input too large')
    return int(b36_string, 36)


def endpoint_cache_key_builder(func: Callable, namespace: str = '', *,
                               request: Request = None, response: Response = None,
                               **kwargs) -> str:
    """
    Returns the key by which cache backend preserves data from response in the cache.
    All params can be contained in the key.
    """
    return ':'.join([
        namespace,
        request.method.lower(),
        request.url.path,
        repr(','.join(f'({k},{v})' for k, v in sorted(request.query_params.items()) if request.query_params))
    ])


class PickleCoderRedis(PickleCoder):
    """
    Codec for encode and decode from Redis cache,
    when Redis respond in bytes format.
    """

    @classmethod
    def encode(cls, value: Any) -> str:
        return codecs.encode(pickle.dumps(value), 'base64').decode()

    @classmethod
    def decode(cls, value: bytes) -> Any:
        return pickle.loads(codecs.decode(value, 'base64'))
