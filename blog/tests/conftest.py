import os
from datetime import timedelta, datetime

import pytest
from faker import Faker
from faker.providers import person
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from httpx import AsyncClient
from sqlalchemy import update, URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy_utils import create_database, database_exists

from accounts.models import User
from common.security import get_password_hash, create_access_token
from common.utils import endpoint_cache_key_builder
from config import get_settings
from db_connection import Base
from dependencies import get_db, oauth2_scheme
from main import app
from posts.models import Post, Category, Comment
from settings.env_dirs import LOGS_DIRECTORY

settings = get_settings()
fake = Faker()
Faker.seed(0)
fake.add_provider(person)

SQLALCHEMY_DATABASE_URL = settings.database_url_test_async

USER_DATA = {
    'username': fake.user_name(),
    'first_name': fake.first_name_female(),
    'last_name': fake.last_name_female(),
    'gender': 'female',
    'email': fake.ascii_email(),
    'password': 'strong_password',
    'date_of_birth': datetime.strftime(fake.date_of_birth(), '%Y-%m-%d'),
    'social_media_links': ['https://facebook.com/users/id=2814984891498911829']
}


def create_db(url: URL) -> None:
    """
    Creates database when was passed `url`,
    which contains driver for asynchronous interaction with database.
    """
    dialect = url.get_dialect(_is_async=True)
    url = f'{dialect.name}://{url.username}:{url.password}@{url.host}:{url.port}/{url.database}'
    create_database(url)


def is_exists_db(url: URL) -> bool:
    """
    Check whether database exists when was passed `url`,
    which contains driver for asynchronous interaction with database.
    """
    dialect = url.get_dialect(_is_async=True)
    url = f'{dialect.name}://{url.username}:{url.password}@{url.host}:{url.port}/{url.database}'
    return database_exists(url)


@pytest.fixture(scope='session')
def anyio_backend():
    """
    Define own anyio_backend fixture because
    the default anyio_backend fixture is function scoped
    """
    return 'asyncio'


@pytest.fixture(scope='session')
async def db_engine(anyio_backend):
    """
    Create database and tables in it, yield this database,
    and remove all tables after all tests will be executed.
    """
    eng = create_async_engine(SQLALCHEMY_DATABASE_URL)
    async with eng.begin() as connection:
        if not is_exists_db(eng.url):
            create_db(eng.url)
        await connection.run_sync(Base.metadata.create_all)

    yield eng

    async with eng.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await eng.dispose()
    clean_log_files_content(LOGS_DIRECTORY)


@pytest.fixture(scope='function')
async def db(db_engine: AsyncEngine):
    """
    Returns session for test database and close database connection
    after all test will be executed.
    """
    async with db_engine.begin() as connection:
        test_db = AsyncSession(bind=connection, expire_on_commit=False)

        yield test_db
        await test_db.rollback()
    await connection.close()


@pytest.fixture(scope='function')
async def client(db: AsyncSession):
    """
    Override dependency for using test database instead of main database
    and create test client for testing api.

    """
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(app=app, base_url='http://test') as ac:
        yield ac
    await ac.aclose()


@pytest.fixture(scope='function')
async def user_for_token(db: AsyncSession):
    """
    Returns user which will be used as current authenticated user,
    and which will has an access token.
    """
    user = User(
        email=fake.unique.ascii_email(),
        hashed_password=get_password_hash(USER_DATA['password']),
        first_name=fake.first_name_male(),
        last_name=fake.last_name_male(),
        gender='male',
        username=fake.unique.first_name_male().lower(),
        date_of_birth=datetime.strptime(USER_DATA['date_of_birth'], '%Y-%m-%d')
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    # make user's account active,
    # since after creating it is inactive by default until user will activate it
    statement = (
        update(User.__table__)
        .where(User.id == user.id)
        .values(**{'is_active': True})
    )
    await db.execute(statement)
    await db.commit()
    await db.refresh(user)
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
async def create_multiple_users(db: AsyncSession):
    """
    Create 2 users and return them.
    """
    user1 = User(
        email=fake.ascii_email(),
        hashed_password=get_password_hash('password1'),
        first_name=fake.first_name_male(),
        last_name=fake.last_name_female(),
        gender='male',
        username=fake.user_name(),
        date_of_birth=datetime.strptime('1965-10-15', '%Y-%m-%d').date()
    )
    user2 = User(
        email=fake.ascii_email(),
        hashed_password=get_password_hash('password2'),
        first_name=fake.first_name_male(),
        last_name=fake.last_name_female(),
        gender='female',
        username=fake.user_name(),
        date_of_birth=datetime.strptime('1978-05-10', '%Y-%m-%d').date()
    )
    db.add_all([user1, user2])
    await db.commit()
    await db.refresh(user1)
    await db.refresh(user2)
    # make users account active,
    # since after creating it is inactive by default until user will activate it
    statement = (
        update(User.__table__)
        .where(User.id.in_([user1.id, user2.id]))
        .values(**{'is_active': True})
    )
    await db.execute(statement)
    await db.commit()
    await db.refresh(user1)
    await db.refresh(user2)
    yield [user1, user2]


@pytest.fixture(scope='function')
async def create_posts_for_user(user_for_token: User, db: AsyncSession):
    """
    Create posts for current authenticated user and return them.
    """
    post_category = Category(name=fake.unique.first_name())
    db.add(post_category)
    await db.commit()
    await db.refresh(post_category)

    post1 = Post(
        title=fake.unique.sentence(nb_words=50),
        body='post_body1',
        tags=['tag1', 'tag2'],
        rating=3,
        is_publish=True,
        category_id=post_category.id,
        owner_id=user_for_token.id
    )
    post2 = Post(
        title=fake.unique.sentence(nb_words=50),
        body='post_body2',
        tags=['tag5', 'tag6', 'tag3', 'tag2'],
        rating=4,
        is_publish=True,
        category_id=post_category.id,
        owner_id=user_for_token.id
    )

    db.add_all([post1, post2])
    await db.commit()
    await db.refresh(post1)
    await db.refresh(post2)
    yield [post1, post2]


@pytest.fixture(scope='function')
async def create_comments_to_posts_for_user(db: AsyncSession, create_posts_for_user: list[Post]):
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

    comment3 = Comment(
        body=f'Comment body3 for post {posts[1].id}',
        post_id=posts[1].id,
        owner_id=posts[0].owner_id
    )

    db.add_all([comment1, comment2, comment3])
    await db.commit()
    await db.refresh(comment1)
    await db.refresh(comment2)
    await db.refresh(comment3)
    yield [comment1, comment2, comment3]


@pytest.fixture(scope='function')
async def create_post_category(db: AsyncSession):
    """
    Create category for posts.
    """
    category = Category(name=fake.unique.first_name())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    yield category


def clean_log_files_content(path: str) -> None:
    """
    Clean log files content after all testing.
    """
    for p in (f'{path}/posts_endpoints.log', f'{path}/users_endpoints.log'):
        if os.path.getsize(p) > 0:
            if os.path.isfile(p):
                with open(p, 'w', encoding='utf-8') as file:
                    file.truncate(0)


@pytest.fixture(scope='function')
def mock_redis(mocker):
    """
    Mock Redis instance for cache.
    """
    mock_redis = mocker.MagicMock(name='blog.main.aioredis')
    mocker.patch('blog.main.aioredis', new=mock_redis)

    FastAPICache.init(RedisBackend(mock_redis), prefix='fastapi-cache', key_builder=endpoint_cache_key_builder)

    yield mock_redis


@pytest.fixture(scope='function')
def mock_smtp(mocker):
    """
    Mock SMTP server to send emails.
    """
    mock_smtp = mocker.MagicMock(name='blog.common.send_email.smtplib.SMTP_SSL')
    mocker.patch('blog.common.send_email.smtplib.SMTP_SSL', new=mock_smtp)

    yield mock_smtp
