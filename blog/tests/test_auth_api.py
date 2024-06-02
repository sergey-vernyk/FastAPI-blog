import pytest
from httpx import AsyncClient
from starlette import status

from accounts.models import User
from common.security import get_token_data
from .conftest import USER_DATA


@pytest.mark.anyio
async def test_login_with_token_success(client: AsyncClient, create_multiple_users: list[User]) -> None:
    """
    Test get access token with scope.
    """
    user_with_token = create_multiple_users[0]

    form_data = {
        'username': user_with_token.username,
        'password': 'password1',
        'scope': 'posts:read'
    }

    response = await client.post(
        url='/auth/login_with_token',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=form_data
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert 'access_token' in response_data and 'token_type' in response_data
    assert response_data['token_type'] == 'bearer'
    # check data from token (scopes and username)
    token_data = get_token_data(response_data['access_token'])
    assert token_data.username == user_with_token.username
    assert token_data.scopes == [form_data['scope']]
    assert len(response.cookies) > 0, 'Must available cookies'
    assert 'csrftoken' in response.cookies, 'Must be csrftoken in the cookies'


@pytest.mark.anyio
async def test_login_with_token_if_passed_user_not_found(client: AsyncClient) -> None:
    """
    Test get access token if user with passed username is not exists.
    """
    form_data = {
        'username': 'not_existing_user',
        'password': 'password1',
        'scope': 'posts:read'
    }

    response = await client.post(
        url='/auth/login_with_token',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=form_data
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'User with passed id does not exists'}


@pytest.mark.anyio
async def test_logout_success(client: AsyncClient, user_for_token: User) -> None:
    """
    Test successfully logging out user from system and deleting CSRF token from its client.
    """
    # authenticating
    form_data = {
        'username': user_for_token.username,
        'password': USER_DATA['password'],
        'scope': 'me:read'
    }

    response = await client.post(
        url='/auth/login_with_token',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=form_data
    )

    assert response.status_code == status.HTTP_200_OK
    assert client.cookies.get('csrftoken') is not None

    # loging out
    response = await client.get(
        url='/auth/logout',
        headers={'Authorization': f'Bearer {response.json()["access_token"]}'}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'detail': f'You ({user_for_token.username}) successfully logged out from the system'}
    assert client.cookies.get('csrftoken') is None


@pytest.mark.anyio
async def test_logout_fail(client: AsyncClient, user_for_token: User) -> None:
    """
    Test logging out user from the system when user is not authenticated.
    """
    response = await client.get(url='/auth/logout')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
    assert client.cookies.get('csrftoken') is None
