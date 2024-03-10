from base64 import urlsafe_b64encode

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio.session import AsyncSession

from accounts.models import User
from accounts.utils import verify_uid_and_token_from_url, token_generator
from common.utils import base36decode, base36encode


def test_base36encode():
    """
    Test converter from integer to base36 string.
    """
    # if number < 36
    actual_result = base36encode(15)
    assert actual_result == 'f'

    # if number > 36
    actual_result = base36encode(125)
    assert actual_result == '3h'

    # if number < 0
    with pytest.raises(ValueError) as exc:
        base36encode(-10)
    assert exc.type is ValueError
    assert exc.value.args[0] == 'Negative base36 conversion input'

    # if number is not an integer
    with pytest.raises(TypeError) as exc:
        base36encode('adc')
    assert exc.type is TypeError
    assert exc.value.args[0] == 'Number must be an integer'


def test_base36_decode():
    """
    Test converter from base36 string into integer.
    """
    actual_result = base36decode('abcd')
    assert actual_result == 481261

    # if length of base36 string exceeds 13
    with pytest.raises(ValueError) as exc:
        base36decode('abcdnhsdkcfsdbfabnvaimugbrviebrvmcriinirnwuxruinpeiiir')
    assert exc.type is ValueError
    assert exc.value.args[0] == 'Base36 input too large'


@pytest.mark.anyio
async def test_verify_uid_and_token_from_url_success(client: AsyncClient,
                                                     user_for_token: User,
                                                     db: AsyncSession) -> None:
    """
    Test verify both uid and token which received from url
    while activating registered account or confirmation resetting password.
    """
    # make token and encode username to base64 format
    # passed these to a test function and in a result
    # we should receive user for who we have made token
    token = token_generator.make_token(user_for_token)
    uidb64 = urlsafe_b64encode(user_for_token.username.encode('utf-8')).decode('utf-8')
    actual_result = await verify_uid_and_token_from_url(db, uidb64, token)
    assert actual_result == user_for_token


@pytest.mark.anyio
async def test_verify_uid_and_token_from_url_wrong_uidb64(client: AsyncClient,
                                                          user_for_token: User,
                                                          create_multiple_users: list[User],
                                                          db: AsyncSession) -> None:
    """
    Test verify both uid and token which received from url
    while activating registered account or confirmation resetting password,
    but uidb64 is wrong.
    """
    token = token_generator.make_token(user_for_token)
    # make uidb64 not for `user_for_token` user
    uidb64 = urlsafe_b64encode(create_multiple_users[0].username.encode('utf-8')).decode('utf-8')
    actual_result = await verify_uid_and_token_from_url(db, uidb64, token)

    assert actual_result is None


@pytest.mark.anyio
async def test_verify_uid_and_token_from_url_wrong_token(client: AsyncClient,
                                                         user_for_token: User,
                                                         create_multiple_users: list[User],
                                                         db: AsyncSession) -> None:
    """
    Test verify both uid and token which received from url
    while activating registered account or confirmation resetting password,
    but token is wrong.
    """
    # make token not for `user_for_token` user
    token = token_generator.make_token(create_multiple_users[0])
    uidb64 = urlsafe_b64encode(user_for_token.username.encode('utf-8')).decode('utf-8')
    actual_result = await verify_uid_and_token_from_url(db, uidb64, token)

    assert actual_result is None
