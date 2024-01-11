from fastapi import status, HTTPException
from starlette.responses import Response


def show_exception(sub: str, error: int) -> HTTPException:
    """
    Returns exception info about `sub` and explanation about `error` type.
    """
    info = {
        status.HTTP_404_NOT_FOUND: f'{sub.capitalize()} with passed id does not exists',
        status.HTTP_403_FORBIDDEN: f'{sub.capitalize()} can be updated only by staff users or by its owner',
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
