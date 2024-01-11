import os.path
import shutil
from base64 import urlsafe_b64encode
from datetime import datetime
from time import sleep
from unittest.mock import patch

from fastapi import status
from fastapi.encoders import jsonable_encoder

from accounts.schemas import UserShow
from accounts.utils import USER_IMAGES_DIR_PATH, token_generator
from common.security import get_token_data
from posts.schemas import UserCommentsShow, UserPostsShow
from .fixtures import *
from ..config import get_settings

TEST_CSRF_TOKEN = 'bvhahncoioerucmigcniquw2cewqc'
settings = get_settings()


def test_create_user_success(client: TestClient, mocker) -> None:
    """
    Test create user with passed parameters.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    # mocking SMTP_SSL server
    mock_smtp = mocker.MagicMock(name='blog.common.send_email.smtplib.SMTP_SSL')
    mocker.patch('blog.common.send_email.smtplib.SMTP_SSL', new=mock_smtp)

    response = client.post(
        url='/users/create',
        headers={'X-CSRFToken': TEST_CSRF_TOKEN},
        json=USER_DATA
    )
    # since we use context manager for create SMTP server we have to use __enter__
    assert mock_smtp.return_value.__enter__.return_value.sendmail.call_count == 1

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data['username'] == USER_DATA['username']
    assert data['email'] == USER_DATA['email']
    assert data['first_name'] == USER_DATA['first_name']
    assert data['last_name'] == USER_DATA['last_name']
    assert data['role'] == 'regular-user'
    assert data['is_active'] is False


def test_create_user_if_email_already_exist(client: TestClient, create_multiple_users: list[User]) -> None:
    """
    Test create user if passed email was already registered by another user.
    """
    current_email = USER_DATA['email']
    # change email for user that will be created on email that had been already registered
    USER_DATA['email'] = create_multiple_users[0].email

    response = client.post(
        url='/users/create',
        json=USER_DATA
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'Email already registered'}
    USER_DATA['email'] = current_email  # replace previous email to avoid errors


def test_create_user_if_username_already_exist(client: TestClient, create_multiple_users: list[User]) -> None:
    """
    Test create user if passed username was already registered by another user.
    """
    current_username = USER_DATA['username']
    # change email for user that will be created on email that had been already registered
    USER_DATA['username'] = create_multiple_users[1].username

    response = client.post(
        url='/users/create',
        json=USER_DATA
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'User with provided username already registered'}
    USER_DATA['username'] = current_username  # replace previous email to avoid errors


def test_read_all_users_with_particular_scope(client: TestClient,
                                              user_for_token: User,
                                              get_token: str,
                                              create_multiple_users: list[User]) -> None:
    """
    Test read all users if user has appropriate access scope.
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


def test_read_all_users_without_particular_scope(client: TestClient, create_multiple_users: list[User]) -> None:
    """
    Test try read all users if user has not appropriate access scope.
    """
    # token withot needed scope
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    response = client.get(
        url='/users/read_all',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_read_user_by_id_with_particular_scope(user_for_token: User, client: TestClient, get_token: str) -> None:
    """
    Test read user by its id if user has appropriate access scope.
    """
    response = client.get(
        url=f'users/read/{user_for_token.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    user_data = jsonable_encoder(user_for_token)
    assert UserShow(**response_data) == UserShow(**user_data)


def test_read_user_by_id_without_particular_scope(user_for_token: User,
                                                  create_multiple_users: list[User],
                                                  client: TestClient) -> None:
    """
    Test read user by its id if has not appropriate access scope.
    """
    # token without needed scope
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    response = client.get(
        url=f'users/read/{user_for_token.id}',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_read_user_by_id_if_passed_wrong_user_id(get_token: str, client: TestClient) -> None:
    """
    Test read user by its id if was passed id that not matched in db.
    """
    response = client.get(
        url='users/read/150',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'User with passed id does not exists'}


def test_read_users_me_if_user_is_active(user_for_token: User, client: TestClient, get_token: str) -> None:
    """
    Test read info about current authenticated user is active now,5
    and has appropriate scope for this action.
    """
    response = client.get(
        url='users/me',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    user_data = jsonable_encoder(user_for_token)
    # check response content
    assert UserShow(**response.json()) == UserShow(**user_data)


def test_read_users_me_if_user_is_inactive(user_for_token: User,
                                           client: TestClient,
                                           get_token: str,
                                           db: Session) -> None:
    """
    Test read info about current authenticated user is inactive.
    """
    # make user inactive
    db.query(User).filter(User.id == user_for_token.id).update({'is_active': False})
    response = client.get(
        url='users/me',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'Inactive user. Activate your account in order to do this action'}


def test_read_users_me_without_particular_scope(create_multiple_users: list[User], client: TestClient) -> None:
    """
    Test read info about current authenticated user has not appropriate access scope.
    """
    # token without needed scope
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    response = client.get(
        url='users/me',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_delete_me_with_particular_scope(user_for_token: User,
                                         client: TestClient,
                                         get_token: str,
                                         db: Session) -> None:
    """
    Test delete current authenticated user if user has appropriate access scope.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = client.delete(
        url='/users/delete/me',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    db_user = db.get(User, user_for_token.id)
    assert db_user is None, 'Current user must be deleted'


def test_delete_me_without_particular_scope(create_multiple_users: list[User], client: TestClient) -> None:
    """
    Test delete current authenticated user if user has not appropriate access scope.
    """
    # token without needed scope
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = client.delete(
        url='/users/delete/me',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_delete_me_if_csrf_tokens_mismatch(create_multiple_users: list[User], client: TestClient) -> None:
    """
    Test delete current authenticated user if csrf tokens in request header and client cookies are mismatch.
    """
    # token without needed scope
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = client.delete(
        url='/users/delete/me',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': 'wrong_crf_token'
        },
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


def test_delete_user_by_id_with_particular_scope(create_multiple_users: list[User],
                                                 client: TestClient,
                                                 get_token: str,
                                                 db: Session) -> None:
    """
    Test delete user from database by `user_id` if user,
    which will delete has appropriate access scope.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    response = client.delete(
        url=f'/users/delete/{create_multiple_users[0].id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    db_user = db.get(User, create_multiple_users[0].id)
    assert db_user is None, f'User with id {create_multiple_users[0].id} must be deleted'


def test_delete_user_by_id_without_particular_scope(create_multiple_users: list[User], client: TestClient) -> None:
    """
    Test delete user from database by `user_id`, if user,
    which will delete has not appropriate access scope.
    """
    # token without needed scope
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    response = client.delete(
        url=f'/users/delete/{create_multiple_users[1].id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_delete_user_by_id_if_passed_wrong_user_id(client: TestClient, get_token: str) -> None:
    """
    Test delete user from database by `user_id`, if passed user id does not exist.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    response = client.delete(
        url='/users/delete/150',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'User with passed id does not exists'}


def test_delete_user_by_id_if_csrf_tokens_mismatch(get_token: str,
                                                   client: TestClient,
                                                   create_multiple_users: list[User]) -> None:
    """
    Test delete user from database by `user_id` if csrf tokens in request header and client cookies are mismatch.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    response = client.delete(
        url=f'/users/delete/{create_multiple_users[1].id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': 'wrong_csrf_token'
        },
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


def test_update_user_info_with_particular_scope(client: TestClient, get_token: str, user_for_token: User) -> None:
    """
    Test update info for current authenticated user if user has appropriate access scope.
    """

    data_to_update = {
        'date_of_birth': '1999-03-12',
        'last_name': 'New Surname'
    }
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = client.patch(
        url='/users/me/update',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json=data_to_update
    )

    assert response.status_code == status.HTTP_200_OK
    assert user_for_token.last_name == data_to_update['last_name']
    assert user_for_token.date_of_birth == datetime.strptime(data_to_update['date_of_birth'], '%Y-%m-%d').date()


def test_update_user_info_without_particular_scope(client: TestClient, create_multiple_users: list[User]) -> None:
    """
    Test update info for current authenticated user if user has not appropriate access scope.
    """
    # token without needed scope
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    data_to_update = {
        'date_of_birth': '1999-03-12',
        'last_name': 'New Surname'
    }
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = client.patch(
        url='/users/me/update',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json=data_to_update
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_update_user_info_if_csrf_tokens_mismatch(client: TestClient, create_multiple_users: list[User]) -> None:
    """
    Test update info for current authenticated user if csrf tokens in request header and client cookies are mismatch.
    """
    # token without needed scope
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    data_to_update = {
        'date_of_birth': '1999-03-12',
        'last_name': 'New Surname'
    }
    client.cookies.set(name='csrftoken', value='wrong_csrf_token')

    response = client.patch(
        url='/users/me/update',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json=data_to_update
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


def test_reset_password_request_if_passed_username_success(client: TestClient, user_for_token: User, mocker) -> None:
    """
    Test reset user's account password using username.
    """
    data_to_reset = {
        'username': user_for_token.username,
        'password': 'new_super_password'
    }
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    mock_smtp = mocker.MagicMock(name='blog.common.send_email.smtplib.SMTP_SSL')
    mocker.patch('blog.common.send_email.smtplib.SMTP_SSL', new=mock_smtp)

    response = client.post(
        url='/users/reset_password',
        json=data_to_reset,
        headers={'X-CSRFToken': TEST_CSRF_TOKEN},
    )

    # since we use context manager for create SMTP server we have to use __enter__
    assert mock_smtp.return_value.__enter__.return_value.sendmail.call_count == 1

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        'detail': 'Check your email! You have to receive email with instruction for reset password'
    }


def test_reset_password_request_if_passed_email_success(client: TestClient, user_for_token: User, mocker) -> None:
    """
    Test reset user's account password using email.
    """
    data_to_reset = {
        'email': user_for_token.email,
        'password': 'new_super_password'
    }
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    mock_smtp = mocker.MagicMock(name='blog.common.send_email.smtplib.SMTP_SSL')
    mocker.patch('blog.common.send_email.smtplib.SMTP_SSL', new=mock_smtp)

    response = client.post(
        url='/users/reset_password',
        json=data_to_reset,
        headers={'X-CSRFToken': TEST_CSRF_TOKEN},
    )

    # since we use context manager for create SMTP server we have to use __enter__
    assert mock_smtp.return_value.__enter__.return_value.sendmail.call_count == 1

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        'detail': 'Check your email! You have to receive email with instruction for reset password'
    }


def test_reset_password_if_was_not_passed_required_data(client: TestClient) -> None:
    """
    Test reset user's account password, when was not passed email or username.
    """
    data_to_reset = {
        'password': 'new_super_password'
    }
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = client.post(
        url='/users/reset_password',
        json=data_to_reset,
        headers={'X-CSRFToken': TEST_CSRF_TOKEN},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'You must provide either username or email for reset password'}


def test_reset_password_if_csrf_tokens_mismatch(client: TestClient) -> None:
    """
    Test reset user's account password if csrf tokens in request header and client cookies are mismatch.
    """
    data_to_reset = {'password': 'new_super_password'}
    client.cookies.set(name='csrftoken', value='wrong_csrf_token')

    response = client.post(
        url='/users/reset_password',
        json=data_to_reset,
        headers={'X-CSRFToken': TEST_CSRF_TOKEN},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


def test_confirm_reset_password_success(client: TestClient, user_for_token: User) -> None:
    """
    Test check if user's account password will really change
    after user will follow link for password reset.
    """
    old_user_password = user_for_token.hashed_password
    uid_pass = (f'{urlsafe_b64encode(get_password_hash("new_password").encode("utf-8")).decode("utf-8")}:'
                f'{urlsafe_b64encode(user_for_token.username.encode("utf-8")).decode("utf-8")}')
    token = token_generator.make_token(user_for_token)

    response = client.get(url=f'/users/confirm_reset_password/{uid_pass}/{token}')

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'detail': 'Password has been changed successfully'}
    assert user_for_token.hashed_password != old_user_password, 'Password must be changed'


def test_confirm_reset_password_fail(client: TestClient, user_for_token: User) -> None:
    """
    Test check when link for password reset confirm is invalid after it has been already used
    or its lifetime has been expired.
    """
    # testing when link has been already used by anyone
    uid_pass = (f'{urlsafe_b64encode(get_password_hash("new_password").encode("utf-8")).decode("utf-8")}:'
                f'{urlsafe_b64encode(user_for_token.username.encode("utf-8")).decode("utf-8")}')
    token = token_generator.make_token(user_for_token)
    # mock request for attempting to confirm reset password
    client.get(url=f'/users/confirm_reset_password/{uid_pass}/{token}')
    response2 = client.get(url=f'/users/confirm_reset_password/{uid_pass}/{token}')

    assert response2.status_code == status.HTTP_200_OK
    assert response2.json() == {'detail': 'Activation link is invalid!'}

    # testing when link has been already expired (token expiration time set to 0)
    with patch.object(token_generator, '_token_expired_time', 0):
        uid_pass = (f'{urlsafe_b64encode(get_password_hash("new_password").encode("utf-8")).decode("utf-8")}:'
                    f'{urlsafe_b64encode(user_for_token.username.encode("utf-8")).decode("utf-8")}')
        token = token_generator.make_token(user_for_token)
        sleep(1)  # do some delay in order to pass test (in debug mode this delay do not necessary)
        response = client.get(url=f'/users/confirm_reset_password/{uid_pass}/{token}')

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'detail': 'Activation link is invalid!'}


def test_login_with_token_success(client: TestClient, create_multiple_users: list[User]) -> None:
    """
    Test get access token with scope.
    """
    user_for_token = create_multiple_users[0]

    form_data = {
        'username': user_for_token.username,
        'password': 'password1',
        'scope': 'posts:read'
    }

    response = client.post(
        url='/users/login_with_token',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=form_data
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert 'access_token' in response_data and 'token_type' in response_data
    assert response_data['token_type'] == 'bearer'
    assert response_data['detail'] == f'Access token was made on username `{user_for_token.username}`'
    # check data from token (scopes and username)
    token_data = get_token_data(response_data['access_token'])
    assert token_data.username == user_for_token.username
    assert token_data.scopes == [form_data['scope']]
    assert len(response.cookies) > 0, 'Must available cookies'
    assert 'csrftoken' in response.cookies, 'Must be csrftoken in the cookies'


def test_login_with_token_if_passed_user_not_found(client: TestClient) -> None:
    """
    Test get access token if user with passed username is not exists.
    """
    form_data = {
        'username': 'not_existing_user',
        'password': 'password1',
        'scope': 'posts:read'
    }

    response = client.post(
        url='/users/login_with_token',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=form_data
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'User with passed id does not exists'}


def test_get_user_posts_without_filter(client: TestClient, get_token: str, create_posts_for_user: list[Post]) -> None:
    """
    Test get all posts, which were written by current authenticated user without using filter.
    """
    response = client.get(
        url='/users/me/posts',
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


def test_get_user_posts_with_filter(client: TestClient, get_token: str, create_posts_for_user: list[Post]) -> None:
    """
    Test get all posts, which were written by current authenticated user with using filter.
    """
    response = client.get(
        url='/users/me/posts',
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
        url='/users/me/posts',
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


def test_get_user_posts_without_particular_scope(client: TestClient, create_multiple_users: list[User]) -> None:
    """
    Test get all posts, which were written by current authenticated,
    if user has not appropriate access scope.
    """
    # token without needed scope
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    response = client.get(
        url='/users/me/posts',
        headers={'Authorization': f'Bearer {token}'},
        params={'apply_filter': False}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_get_users_comment_with_particular_scope(client: TestClient,
                                                 create_comments_for_user: list[Comment],
                                                 get_token: str) -> None:
    """
    Test get all posts of current authenticated user is user has appropriate access scope.
    """
    response = client.get(
        url='/users/me/comments',
        headers={'Authorization': f'Bearer {get_token}'},
        params={'rate_status': 'all'}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data) == 2, 'Must 2 comments'
    # check whether response comment data equal data of already created comments
    assert UserCommentsShow(**response_data[0]) == UserCommentsShow(**jsonable_encoder(create_comments_for_user[0]))
    assert UserCommentsShow(**response_data[1]) == UserCommentsShow(**jsonable_encoder(create_comments_for_user[1]))


def test_get_users_comment_without_particular_scope(client: TestClient, create_multiple_users: list[User]) -> None:
    """
    Test get all posts of current authenticated user if user has not appropriate access scope.
    """
    # token without needed scope
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    response = client.get(
        url='/users/me/comments',
        headers={'Authorization': f'Bearer {token}'},
        params={'rate_status': 'all'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_create_user_photo_with_particular_scope(client: TestClient, get_token: str, user_for_token: User) -> None:
    """
    Test create current user's photo, if user has appropriate access scope.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    image = open('blog/tests/avatar.png', 'rb')

    response = client.post(
        url='/users/upload_user_image',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN,
        },
        files={'image': image}
    )

    image.close()
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'detail': 'Image `avatar.png` has been successfully uploaded'}
    assert os.path.isfile(f'{USER_IMAGES_DIR_PATH}{user_for_token.username}/avatar.png') is True
    # delete user's directory with image
    shutil.rmtree(f'{USER_IMAGES_DIR_PATH}{user_for_token.username}')


def test_create_user_photo_if_csrf_tokens_mismatch(client: TestClient, get_token: str) -> None:
    """
    Test create current user's photo, if csrf tokens in request header and client cookies are mismatch.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    image = open('blog/tests/avatar.png', 'rb')

    response = client.post(
        url='/users/upload_user_image',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': 'wrong_csrf_token',
        },
        files={'image': image}
    )

    image.close()
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


def test_create_user_photo_without_particular_scope(client: TestClient, create_multiple_users: list[User]) -> None:
    """
    Test create current user's photo, if user has not appropriate access scope.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    image = open('blog/tests/avatar.png', 'rb')

    response = client.post(
        url='/users/upload_user_image',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN,
        },
        files={'image': image}
    )

    image.close()
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}
