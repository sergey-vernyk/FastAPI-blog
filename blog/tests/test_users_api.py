from datetime import timedelta

import pytest
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy_utils.functions import create_database, database_exists

from accounts.models import User
from accounts.security import get_password_hash, create_access_token
from db_connection import Base
from dependencies import get_db
from main import app
from .config_test import SQLALCHEMY_DATABASE_URL

USER_DATA = {
    'username': 'test_user',
    'first_name': 'Test',
    'last_name': 'User',
    'gender': 'female',
    'email': 'example@example.com',
    'password': 'strong_password',
    'date_of_birth': '1990-12-09',
}


@pytest.fixture(scope='session')
def db_engine():
    """
    Create database and tables in it, yield this database,
    and remove all tables after all tests will be executed.
    """
    eng = create_engine(SQLALCHEMY_DATABASE_URL)
    if not database_exists(eng.url):
        create_database(eng.url)

    Base.metadata.create_all(bind=eng)

    yield eng

    Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope='function')
def db(db_engine):
    """
    Returns session for test database and close database connection
    after all test will be executed.
    """
    connection = db_engine.connect()
    connection.begin()
    test_db = Session(bind=connection)

    yield test_db

    test_db.rollback()
    connection.close()


@pytest.fixture(scope='function')
def client(db):
    """
    Override dependency for using test database instead of main database
    and create test client for testing api.

    """
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as c:
        yield c


@pytest.fixture
def get_token(client, user_for_token):
    """
    Returns access token for `user_for_token` user.
    """
    token_data = {
        'username': user_for_token.username,
        'password': 'strong_password',
        'scopes': 'post:create category:create post:read post:update post:delete '
                  'comment:update comment:delete comment:create comment:rate user:read '
                  'user:update user:delete me:delete me:update me:read'.split()
    }
    token = create_access_token(data={'sub': user_for_token.username, 'scopes': token_data['scopes']},
                                expires_delta=timedelta(minutes=5))
    yield token


@pytest.fixture(scope='function')
def user_for_token(db):
    """
    Returns user which will be used as current authenticated user,
    and which will has an access token.
    """
    user = User(
        email=USER_DATA['email'],
        hashed_password=get_password_hash(USER_DATA['password']),
        first_name=USER_DATA['first_name'],
        last_name=USER_DATA['last_name'],
        gender=USER_DATA['gender'],
        username=USER_DATA['username'],
        date_of_birth=USER_DATA['date_of_birth']
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user


@pytest.fixture(scope='function')
def multiple_users(db):
    """
    Create 2 users and return them.
    """
    user1 = User(
        email='example1@example.com',
        hashed_password=get_password_hash('password1'),
        first_name='name1',
        last_name='surname1',
        gender='male',
        username='user1',
        date_of_birth='1965-10-15'
    )
    user2 = User(
        email='example2@example.com',
        hashed_password=get_password_hash('password2'),
        first_name='name2',
        last_name='surname2',
        gender='female',
        username='user2',
        date_of_birth='1978-05-10'
    )
    db.add_all([user1, user2])
    db.commit()
    yield [user1, user2]


def test_create_user(client):
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


def test_read_all_users(client, get_token, multiple_users):
    """
    Test read all users in a database.
    """
    response = client.get(
        url='/users/read_all',
        headers={'Authorization': f'Bearer {get_token}'}
    )
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data) == 3, 'Must be 3 users'
    assert isinstance(response_data, list), 'Must be list type'

    user_data = response_data[0]
    assert user_data['username'] == USER_DATA['username']
    assert user_data['email'] == USER_DATA['email']
    assert user_data['first_name'] == USER_DATA['first_name']
    assert user_data['last_name'] == USER_DATA['last_name']
    assert user_data['role'] == 'regular user'
    assert user_data['is_active'] is True
    assert user_data['gender'] == USER_DATA['gender']

    user1_data = jsonable_encoder(multiple_users[0])
    user1_data.pop('hashed_password')
    user2_data = jsonable_encoder(multiple_users[1])
    user2_data.pop('hashed_password')
    assert user1_data == response_data[1]
    assert user2_data == response_data[2]


def test_read_user_by_id(user_for_token, client, get_token):
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
    user_data.pop('hashed_password')
    assert response_data == user_data


def test_read_me(user_for_token, client, get_token):
    """
    Test read info about current authenticated user.
    """
    response = client.get(
        url='users/me',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    user_data = jsonable_encoder(user_for_token)
    user_data.pop('hashed_password')
    assert response.json() == user_data
