from datetime import datetime

from fastapi import HTTPException, status
from jose import jwt
from pytest import raises

from accounts.schemas import TokenData
from accounts.security import verify_password_or_exception, get_token_data
from config import Settings
from .fixtures import *

settings = Settings()


def test_verify_passed_passwords_for_authentication_success(user_for_token: User) -> None:
    """
    Test verify plain password from `frontend` and current hashed user password,
    if verify going without exception.
    """
    plain_password, hashed_password = USER_DATA['password'], user_for_token.hashed_password
    assert verify_password_or_exception(hashed_password, plain_password) is None


def test_verify_passed_passwords_for_authentication_fail(user_for_token: User) -> None:
    """
    Test verify plain password from `frontend` and current hashed user password,
    if verify ends with exception (passwords are mismatch).
    """
    with raises(HTTPException) as ex:
        plain_password, hashed_password = 'wrong_password', user_for_token.hashed_password
        verify_password_or_exception(hashed_password, plain_password)
    assert ex.value.detail == 'Incorrect password'
    assert ex.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert ex.value.headers == {'WWW-Authenticate': 'Bearer'}


def test_get_token_data(get_token: str, user_for_token: User):
    """
    Test get and verify data from access token.
    """
    token_data = get_token_data(get_token)
    assert isinstance(token_data, TokenData)
    assert token_data.username == user_for_token.username
    assert len(token_data.scopes) > 0


def test_create_access_token(create_multiple_users: list[User]) -> None:
    data = {
        'sub': create_multiple_users[0].username,
        'scopes': ['scope:read', 'scope:write', 'scope:delete']
    }
    # pass timedelta into token data
    token = create_access_token(data, timedelta(minutes=5))
    decoded_token = jwt.decode(token, key=settings.secret_key, algorithms=[settings.algorithm])
    assert decoded_token['sub'] == create_multiple_users[0].username
    assert decoded_token['scopes'] == data['scopes']
    # check whether access token has not expired
    assert datetime.fromtimestamp(decoded_token['exp']) - datetime.now() <= timedelta(
        minutes=5), 'Token have already expired'
