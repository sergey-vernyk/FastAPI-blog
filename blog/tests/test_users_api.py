from datetime import datetime

from fastapi import status
from fastapi.encoders import jsonable_encoder

from accounts.schemas import UserShow
from accounts.security import get_token_data
from posts.schemas import UserCommentsShow, UserPostsShow
from .fixtures import *


def test_create_user(client: TestClient):
    """
    Test create user with passed parameters.
    """
    response = client.post(url='/users/create', json=USER_DATA)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data['username'] == USER_DATA['username']
    assert data['email'] == USER_DATA['email']
    assert data['first_name'] == USER_DATA['first_name']
    assert data['last_name'] == USER_DATA['last_name']
    assert data['role'] == 'regular user'
    assert data['is_active'] is True


def test_read_all_users(client: TestClient, user_for_token: User, get_token: str, create_multiple_users: list[User]):
    """
    Test read all users from a database.
    """
    response = client.get(
        url='/users/read_all',
        headers={'Authorization': f'Bearer {get_token}'}
    )
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data) == 3, 'Must be 3 users'
    assert isinstance(response_data, list), 'Must be list type'

    user_data1 = response_data[0]
    user_data2 = response_data[1]
    user_data3 = response_data[2]
    # compare already exist users info with info from response
    assert UserShow(**jsonable_encoder(user_for_token)) == UserShow(**user_data1)
    assert UserShow(**jsonable_encoder(create_multiple_users[0])) == UserShow(**user_data2)
    assert UserShow(**jsonable_encoder(create_multiple_users[1])) == UserShow(**user_data3)


def test_read_user_by_id(user_for_token: User, client: TestClient, get_token: str):
    """
    Test read user by its id.
    """
    response = client.get(
        url=f'users/read/{user_for_token.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    user_data = jsonable_encoder(user_for_token)
    assert UserShow(**response_data) == UserShow(**user_data)


def test_read_users_me(user_for_token: User, client: TestClient, get_token: str):
    """
    Test read info about current authenticated user.
    """
    response = client.get(
        url='users/me',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    user_data = jsonable_encoder(user_for_token)
    # check response content
    assert UserShow(**response.json()) == UserShow(**user_data)


def test_delete_me(user_for_token: User, client: TestClient, get_token: str, db: Session):
    """
    Test delete current authenticated user.
    """
    response = client.delete(
        url='/users/delete/me',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    db_user = db.get(User, user_for_token.id)
    assert db_user is None, 'Current user must be deleted'


def test_delete_user_by_id(create_multiple_users: list[User], client: TestClient, get_token: str, db: Session):
    """
    Test delete user from database by `user_id`.
    """
    response = client.delete(
        url=f'/users/delete/{create_multiple_users[0].id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    db_user = db.get(User, create_multiple_users[0].id)
    assert db_user is None, f'User with id {create_multiple_users[0].id} must be deleted'


def test_update_user_info(client: TestClient, get_token: str, user_for_token: User):
    """
    Test update info for current authenticated user.
    """

    data_to_update = {
        'date_of_birth': '1999-03-12',
        'last_name': 'New Surname'
    }
    response = client.patch(
        url='/users/me/update',
        headers={'Authorization': f'Bearer {get_token}'},
        json=data_to_update
    )

    assert response.status_code == status.HTTP_200_OK
    assert user_for_token.last_name == data_to_update['last_name']
    assert user_for_token.date_of_birth == datetime.strptime(data_to_update['date_of_birth'], '%Y-%m-%d').date()


def test_reset_password_success(client: TestClient, user_for_token: User):
    """
    Test reset user's account password using username or email.
    """
    previous_password = user_for_token.hashed_password
    data_to_reset = {
        'username': user_for_token.username,
        'password': 'new_super_password'
    }

    response = client.post(
        url='/users/reset_password',
        json=data_to_reset
    )

    assert response.status_code == status.HTTP_200_OK
    assert user_for_token.hashed_password != previous_password, 'Password was not changed'
    assert response.json() == {'success': 'Password has been changed successfully'}

    # email for password reset instead of username
    data_to_reset.pop('username')
    data_to_reset['email'] = user_for_token.email

    response = client.post(
        url='/users/reset_password',
        json=data_to_reset
    )

    assert response.status_code == status.HTTP_200_OK
    assert user_for_token.hashed_password != previous_password, 'Password was not changed'
    assert response.json() == {'success': 'Password has been changed successfully'}


def test_reset_password_fail(client: TestClient):
    """
    Test reset user's account password, but when was not passed email or username.
    """
    data_to_reset = {
        'password': 'new_super_password'
    }

    response = client.post(
        url='/users/reset_password',
        json=data_to_reset
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'Username or email was not passed'}


def test_login_for_token(client: TestClient, create_multiple_users: list[User]):
    user_for_token = create_multiple_users[0]

    form_data = {
        'username': user_for_token.username,
        'password': 'password1',
        'scope': 'posts:read'
    }

    response = client.post(
        url='/users/token',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=form_data
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert 'access_token' in response_data and 'token_type' in response_data
    assert response_data['token_type'] == 'bearer'
    # check data from token (scopes and username)
    token_data = get_token_data(response_data['access_token'])
    assert token_data.username == user_for_token.username
    assert token_data.scopes == [form_data['scope']]


def test_get_user_posts_without_filter(client: TestClient, get_token: str, create_posts_for_user: list[Post]):
    """
    Test get all posts, which were written by current authenticated user without using filter.
    """
    response = client.get(
        url='/users/posts/me',
        headers={'Authorization': f'Bearer {get_token}'},
        params={'apply_filter': False}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    existed_post1_data = jsonable_encoder(create_posts_for_user[0])
    existed_post2_data = jsonable_encoder(create_posts_for_user[1])
    # check whether response post data equal data of already created posts
    assert UserPostsShow(**response_data[0]) == UserPostsShow(**existed_post1_data)
    assert UserPostsShow(**response_data[1]) == UserPostsShow(**existed_post2_data)


def test_get_user_posts_with_filter(client: TestClient, get_token: str, create_posts_for_user: list[Post]):
    """
    Test get all posts, which were written by current authenticated user with using filter.
    """
    response = client.get(
        url='/users/posts/me',
        headers={'Authorization': f'Bearer {get_token}'},
        params={
            'apply_filter': True,
            'tags': 'tag3',
            'is_publish': True,
            'rating': 0,  # 0 or above
            'category': ''
        }
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data) == 1, 'Must be only one post'
    post_data = jsonable_encoder(create_posts_for_user[1])
    # check whether response post data equal data of already created post
    assert UserPostsShow(**jsonable_encoder(create_posts_for_user[1])) == UserPostsShow(
        **post_data), 'Must be only second post'

    response = client.get(
        url='/users/posts/me',
        headers={'Authorization': f'Bearer {get_token}'},
        params={
            'apply_filter': True,
            'tags': 'tag2',
            'is_publish': True,
            'rating': 0,  # 0 or above
            'category': ''
        }
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data) == 2, 'Must be two posts'


def test_get_users_comment(client: TestClient, create_comments_for_user: list[Comment], get_token: str):
    """
    Test get all posts of current authenticated user.
    """
    response = client.get(
        url='/users/comments/me',
        headers={'Authorization': f'Bearer {get_token}'},
        params={'rate_status': 'all'}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data) == 2, 'Must 2 comments'
    # check whether response comment data equal data of already created comments
    assert UserCommentsShow(**response_data[0]) == UserCommentsShow(**jsonable_encoder(create_comments_for_user[0]))
    assert UserCommentsShow(**response_data[1]) == UserCommentsShow(**jsonable_encoder(create_comments_for_user[1]))
