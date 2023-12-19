from datetime import timedelta
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy_utils.functions import create_database, database_exists

from accounts.models import User
from accounts.security import get_password_hash, create_access_token
from db_connection import Base
from dependencies import get_db
from dependencies import oauth2_scheme
from main import app
from posts.models import Post, Category, Comment
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
def db_engine() -> Generator[Engine, None, None]:
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
def db(db_engine: Engine):
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
def client(db: Session):
    """
    Override dependency for using test database instead of main database
    and create test client for testing api.

    """
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope='function')
def user_for_token(db: Session):
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
def get_token(user_for_token: User):
    """
    Returns access token for `user_for_token` user with token's scopes.
    """
    scopes = list(oauth2_scheme.model.model_dump()['flows']['password']['scopes'].keys())
    token = create_access_token(data={'sub': user_for_token.username, 'scopes': scopes},
                                expires_delta=timedelta(minutes=5))
    yield token


@pytest.fixture(scope='function')
def create_multiple_users(db: Session):
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


@pytest.fixture(scope='function')
def create_posts_for_user(user_for_token: User, db: Session):
    """
    Create posts for current authenticated user and return them.
    """
    post_category = Category(name='post_category')
    db.add(post_category)
    db.commit()
    db.refresh(post_category)

    post1 = Post(
        title='post_title1',
        body='post_body1',
        tags='tag1,tag2',
        rating=3,
        is_publish=True,
        category_id=post_category.id,
        owner_id=user_for_token.id
    )
    post2 = Post(
        title='post_title2',
        body='post_body2',
        tags='tag5,tag6,tag3,tag2',
        rating=4,
        is_publish=True,
        category_id=post_category.id,
        owner_id=user_for_token.id
    )
    db.add_all([post1, post2])
    db.commit()
    db.refresh(post1)
    db.refresh(post2)
    yield [post1, post2]


@pytest.fixture(scope='function')
def create_comments_for_user(db: Session, create_posts_for_user: list[Post]):
    """
    Create comments for posts, owner of which is current authenticated user.
    """
    posts = create_posts_for_user
    comment1 = Comment(
        body=f'Comment body1 for post {posts[0].id}',
        post_id=posts[0].id,
        owner_id=posts[0].owner_id
    )
    comment2 = Comment(
        body=f'Comment body2 for post {posts[1].id}',
        post_id=posts[1].id,
        owner_id=posts[0].owner_id
    )

    db.add_all([comment1, comment2])
    db.commit()
    db.refresh(comment1)
    db.refresh(comment2)
    yield [comment1, comment2]


@pytest.fixture(scope='function')
def create_post_category(db: Session):
    """
    Create category for posts.
    """
    category = Category(name='Category name')
    db.add(category)
    db.commit()
    db.refresh(category)
    yield category
