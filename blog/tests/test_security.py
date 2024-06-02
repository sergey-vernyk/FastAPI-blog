from datetime import datetime, timedelta

import pytest
from accounts.auth.schemas import TokenData
from accounts.models import User
from accounts.utils import LimitedLifeTokenGenerator
from common.security import (create_access_token, get_password_hash,
                             get_token_data, verify_password_or_exception)
from config import get_settings
from fastapi import HTTPException, status
from jose import jwt
from pytest import raises
from pytz import utc
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from .conftest import USER_DATA

settings = get_settings()


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
    """
    Test create access JWT token with scopes and verify its expiry date.
    """
    data = {'sub': create_multiple_users[0].username, 'scopes': ['scope:read', 'scope:write', 'scope:delete']}
    # pass timedelta into token data
    token = create_access_token(data, timedelta(minutes=5))
    decoded_token = jwt.decode(token, key=settings.secret_key, algorithms=[settings.algorithm])
    assert decoded_token['sub'] == create_multiple_users[0].username
    assert decoded_token['scopes'] == data['scopes']
    # check whether access token has not expired
    assert datetime.fromtimestamp(decoded_token['exp'], tz=utc) - datetime.now(tz=utc) <= timedelta(
        minutes=5
    ), 'Token have already expired'


def test_create_access_token_if_not_passed_expire_time(create_multiple_users: list[User]) -> None:
    """
    Test create access JWT token with scopes and verify its expiry date,
    if there was not passed expire time for the token.
    """
    data = {'sub': create_multiple_users[0].username, 'scopes': ['scope:read', 'scope:write', 'scope:delete']}
    # pass timedelta into token data
    token = create_access_token(data)
    decoded_token = jwt.decode(token, key=settings.secret_key, algorithms=[settings.algorithm])
    assert decoded_token['sub'] == create_multiple_users[0].username
    assert decoded_token['scopes'] == data['scopes']
    # check whether access token has not expired
    assert datetime.fromtimestamp(decoded_token['exp']) - datetime.now() <= timedelta(
        minutes=15
    ), 'Token have already expired'


class TestLimitedLifeTokenGenerator:

    def setup_method(self) -> None:
        self.token_generator = LimitedLifeTokenGenerator(
            secret_key=settings.secret_key_token_generator, token_expired_timeout=10
        )

    def test_make_token(self, user_for_token) -> None:
        """
        Test make limited life token. We can check only availability of token,
        and its format, since generator makes different token each time.
        """
        token = self.token_generator.make_token(user_for_token)
        assert len(token) > 0
        assert '-' in token

    def test_check_token_success(self, user_for_token) -> None:
        """
        Test check generated token if there were no conditions
        to change hash value which token contains.
        """
        token = self.token_generator.make_token(user_for_token)
        result = self.token_generator.check_token(user_for_token, token)
        assert result is True

    @pytest.mark.anyio
    async def test_check_token_if_changed_hash_value(self, user_for_token, db: AsyncSession) -> None:
        """
        Test check generated token when it has been changed i.e. when has been changed token's hash value.
        User's data could has been changed (e.g. password, email, last login timestamp etc.)
        """
        token = self.token_generator.make_token(user_for_token)
        new_password = get_password_hash('new_strong_password')
        await db.execute(
            update(User.__table__).where(User.id == user_for_token.id).values(**{'hashed_password': new_password})
        )
        await db.commit()
        await db.refresh(user_for_token)
        result = self.token_generator.check_token(user_for_token, token)
        assert result is False

    @pytest.mark.anyio
    async def test_check_token_return_false(self, user_for_token, db: AsyncSession) -> None:
        """
        Test check the generated token when there were
        conditions which leads to that token becomes invalid.
        """
        token = self.token_generator.make_token(user_for_token)

        # if function for checking token state has not received `user` or `token`
        actual_result = self.token_generator.check_token(token, '')
        assert actual_result is False

        # if token has incorrect format (without hyphen inside)
        actual_result = self.token_generator.check_token(user_for_token, 'lkmkvmowevowenownefwfin')
        assert actual_result is False

        # if token has been expired
        self.token_generator._token_expired_time = -1
        token = self.token_generator.make_token(user_for_token)
        actual_result = self.token_generator.check_token(user_for_token, token)
        assert actual_result is False

        # if token's timestamp has not been decoded correctly (encoded timestamp has length more than 13 symbols)
        actual_result = self.token_generator.check_token(user_for_token, 'lkmkvictonuntixru-mowevowenownefwfinclmg')
        assert actual_result is False
