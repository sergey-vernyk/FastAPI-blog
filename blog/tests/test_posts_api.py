from datetime import timedelta

import pytest
from fastapi import status
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from accounts.models import User
from accounts.schemas import UserShowBriefly
from common.security import create_access_token
from posts.models import Comment, Post, Category
from posts.schemas import (
    PostShow, PostUpdate,
    CategoryCreate, CommentShow,
    Category as CategorySchema
)
from .conftest import fake

POST_DATA = {
    'title': fake.unique.sentence(nb_words=50),
    'body': 'Post body',
    'tags': ['tag1', 'tag2']
}

TEST_CSRF_TOKEN = 'bvhahncoioerucmigcniquw2cewqc'


@pytest.mark.anyio
async def test_create_post_with_authorization(client: AsyncClient,
                                              create_post_category: Category,
                                              get_token: str,
                                              db: AsyncSession) -> None:
    """
    Test create post behalf current authenticated user.
    """
    POST_DATA.update(category=create_post_category.name)
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.post(
        url='/posts/create',
        json=POST_DATA,
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    buffered_post = await db.execute(
        select(Post)
        .where(Post.id == response_data['id'])
    )
    created_post = buffered_post.scalar()
    created_post_dict = jsonable_encoder(created_post)
    created_post_dict.update(
        tags=created_post.tags,
        owner=UserShowBriefly(id=created_post.owner_id, username=created_post.owner.username),
        category=CategoryCreate(name=created_post.category.name)
    )
    assert PostShow(**response_data) == PostShow(**created_post_dict)


@pytest.mark.anyio
async def test_create_post_without_authentication(client: AsyncClient,
                                                  create_post_category: Category,
                                                  user_for_token: User) -> None:
    """
    Test create post without authentication.
    """
    POST_DATA.update(category=create_post_category.name,
                     owner=user_for_token.username)
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.post(
        url='/posts/create',
        json=POST_DATA,
        headers={'X-CSRFToken': TEST_CSRF_TOKEN}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not authenticated'}


@pytest.mark.anyio
async def test_create_post_if_csrf_tokens_mismatch(client: AsyncClient,
                                                   create_post_category: Category,
                                                   user_for_token: User) -> None:
    """
    Test create post if csrf tokens in request header and client cookies are mismatch
    """
    POST_DATA.update(category=create_post_category.name,
                     owner=user_for_token.username)
    client.cookies.set(name='csrftoken', value='wrong_csrf_token')

    response = await client.post(
        url='/posts/create',
        json=POST_DATA,
        headers={'X-CSRFToken': TEST_CSRF_TOKEN}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


@pytest.mark.anyio
async def test_create_post_without_particular_scopes(client: AsyncClient,
                                                     create_post_category: Category,
                                                     create_multiple_users: list[User]) -> None:
    """
    Test create post without particular scope for endpoint.
    """
    POST_DATA.update(category=create_post_category.name,
                     owner=create_multiple_users[0].username)
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.post(
        url='/posts/create',
        json=POST_DATA,
        # token without particular scope
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


@pytest.mark.anyio
async def test_create_category_with_authorization(client: AsyncClient, get_token: str) -> None:
    """
    Test create category for posts.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.post(
        url='/posts/categories/create',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json={'name': 'Computers'}
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()['name'] == 'Computers'


@pytest.mark.anyio
async def test_create_category_without_authentication(client: AsyncClient) -> None:
    """
    Test create category for posts without authentication.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.post(
        url='/posts/categories/create',
        headers={'X-CSRFToken': TEST_CSRF_TOKEN},
        json={'name': 'Computers'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not authenticated'}


@pytest.mark.anyio
async def test_create_category_without_particular_scopes(client: AsyncClient,
                                                         create_multiple_users: list[User]) -> None:
    """
    Test create category for posts without authorization with appropriate scope
    """
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.post(
        url='/posts/categories/create',
        json={'name': 'Computers'},
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


@pytest.mark.anyio
async def test_create_category_if_csrf_tokens_mismatch(client: AsyncClient, get_token: str) -> None:
    """
    Test create category for posts if csrf tokens in request header and client cookies are mismatch.
    """
    client.cookies.set(name='csrftoken', value='wrong_csrf_token')

    response = await client.post(
        url='/posts/categories/create',
        json={'name': 'Computers'},
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


@pytest.mark.anyio
async def test_read_post(client: AsyncClient, create_posts_for_user: list[Post], mock_redis) -> None:
    """
    Test read post by its id.
    """
    post_for_receiving = create_posts_for_user[1]
    response = await client.get(
        url=f'posts/read/{post_for_receiving.id}',
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    post_data_dict = jsonable_encoder(post_for_receiving)
    post_data_dict.update(
        tags=post_for_receiving.tags,
        owner=UserShowBriefly(id=post_for_receiving.owner_id, username=post_for_receiving.owner.username),
        category=CategoryCreate(name=post_for_receiving.category.name)
    )
    assert PostShow(**response_data) == PostShow(**post_data_dict)


@pytest.mark.anyio
async def test_read_posts(client: AsyncClient, create_posts_for_user: list[Post], mock_redis, db: AsyncSession) -> None:
    """
    Test read all posts in the database.
    """
    response = await client.get(url='posts/posts/read_all', params={'sort_by': 'created_desc'})

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # sort response data because we must be sure that data will always be in the same ordering
    response_data_sorted = sorted(response_data, key=lambda i: i['id'])

    assert len(response_data_sorted) == 2

    for p in zip(response_data_sorted, create_posts_for_user):
        posts_data = jsonable_encoder(p[1])
        posts_data.update(
            tags=p[1].tags,
            owner=UserShowBriefly(id=p[1].owner_id, username=p[1].owner.username),
            category=CategoryCreate(name=p[1].category.name)
        )

        assert PostShow(**p[0]) == PostShow(**posts_data)


@pytest.mark.anyio
async def test_read_posts_sort_by_rating(client: AsyncClient,
                                         create_posts_for_user: list[Post],
                                         mock_redis,
                                         db: AsyncSession) -> None:
    """
    Test read all posts in the database.
    """
    post_rating4 = create_posts_for_user[1]
    post_rating3 = create_posts_for_user[0]
    response = await client.get(url='posts/posts/read_all', params={'sort_by': 'rating_desc'})

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert len(response_data) == 2

    # post with rating 4 must be first in the response (index 0)
    post_data = jsonable_encoder(post_rating4)
    post_data.update(
        tags=post_rating4.tags,
        owner=UserShowBriefly(id=post_rating4.owner_id, username=post_rating4.owner.username),
        category=CategoryCreate(name=post_rating4.category.name)
    )
    assert PostShow(**response_data[0]) == PostShow(**post_data)

    # post with rating 4 must be second in the response (index 1)
    post_data = jsonable_encoder(post_rating3)
    post_data.update(
        tags=post_rating3.tags,
        owner=UserShowBriefly(id=post_rating3.owner_id, username=post_rating3.owner.username),
        category=CategoryCreate(name=post_rating3.category.name)
    )
    assert PostShow(**response_data[1]) == PostShow(**post_data)


@pytest.mark.anyio
async def test_read_post_category(client: AsyncClient,
                                  create_post_category: Category,
                                  mock_redis) -> None:
    """
    Test read one post category.
    """
    response = await client.get(url=f'/posts/categories/read/{create_post_category.id}')
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), dict)
    assert CategorySchema(**response.json()) == CategorySchema(**jsonable_encoder(create_post_category))


@pytest.mark.anyio
async def test_read_post_category_if_category_not_exists(client: AsyncClient,
                                                         create_post_category: Category,
                                                         mock_redis) -> None:
    """
    Test read one post category.
    """
    response = await client.get(url='/posts/categories/read/155')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Category with passed id does not exists'}


@pytest.mark.anyio
async def test_read_post_categories(client: AsyncClient,
                                    create_post_category: Category,
                                    db: AsyncSession,
                                    mock_redis) -> None:
    """
    Test read all posts categories.
    """
    response = await client.get(url='/posts/categories/read_all')
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data) == 1
    assert CategorySchema(**jsonable_encoder(create_post_category)) == CategorySchema(**response_data[0])


@pytest.mark.anyio
async def test_update_post_with_authorization(client: AsyncClient,
                                              create_posts_for_user: list[Post],
                                              get_token: str) -> None:
    """
    Update post by passed post_id with corresponding authorization scope.
    """
    post_for_update = create_posts_for_user[0]
    post_data = jsonable_encoder(post_for_update)
    post_data.update(rating=4,
                     body='post_body_updated',
                     tags=post_data['tags'],
                     category=post_for_update.category.name)
    post_update_body = PostUpdate(**post_data)
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.put(
        url=f'/posts/update/{post_for_update.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json=post_update_body.model_dump()
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    expected_data = PostShow(id=post_for_update.id,
                             title=post_for_update.title,
                             tags=post_data['tags'],
                             body=post_data['body'],
                             category=CategoryCreate(name=post_data['category']),
                             rating=post_data['rating'],
                             updated=create_posts_for_user[0].updated,
                             created=create_posts_for_user[0].created,
                             owner=UserShowBriefly(id=post_for_update.owner_id,
                                                   username=post_for_update.owner.username),
                             is_publish=post_for_update.is_publish,
                             count_comments=0,
                             comments=[])
    assert PostShow(**response_data) == expected_data


@pytest.mark.anyio
async def test_update_post_without_authentication(client: AsyncClient, create_posts_for_user: list[Post]) -> None:
    """
    Update post by passed post_id without authentication.
    """
    post_for_update = create_posts_for_user[0]
    post_data = jsonable_encoder(post_for_update)
    post_data.update(rating=4,
                     body='post_body_updated',
                     tags=post_data['tags'],
                     category=post_for_update.category.name)
    post_update_body = PostUpdate(**post_data)
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.put(
        url=f'/posts/update/{post_for_update.id}',
        json=post_update_body.model_dump(),
        headers={'X-CSRFToken': TEST_CSRF_TOKEN}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not authenticated'}


@pytest.mark.anyio
async def test_update_post_if_csrf_tokens_mismatch(client: AsyncClient, create_posts_for_user: list[Post]) -> None:
    """
    Update post by passed post_id if csrf tokens in request header and client cookies are mismatch.
    """
    post_for_update = create_posts_for_user[0]
    post_data = jsonable_encoder(post_for_update)
    post_data.update(rating=4,
                     body='post_body_updated',
                     tags=post_data['tags'],
                     category=post_for_update.category.name)
    post_update_body = PostUpdate(**post_data)
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.put(
        url=f'/posts/update/{post_for_update.id}',
        json=post_update_body.model_dump(),
        headers={'X-CSRFToken': 'wrong_csrf_token'}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


@pytest.mark.anyio
async def test_delete_post_with_authorization(client: AsyncClient,
                                              get_token: str,
                                              create_posts_for_user: list[Post],
                                              db: AsyncSession):
    """
    Test delete post if user has appropriate authorization scope, and it is a post's owner.
    """
    post_for_delete = create_posts_for_user[1]
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.delete(
        url=f'posts/delete/{post_for_delete.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    buffered_post = await db.execute(
        select(Post)
        .where(Post.id == post_for_delete.id)
    )
    assert buffered_post.scalar() is None


@pytest.mark.anyio
async def test_delete_post_not_by_its_owner(client: AsyncClient,
                                            create_multiple_users: list[User],
                                            create_posts_for_user: list[Post]) -> None:
    """
    Test delete post if user is not the owner of this post.
    """
    post_for_delete = create_posts_for_user[1]
    # user allow to delete post, but it is not post's owner
    user = create_multiple_users[0]
    token = create_access_token(data={'sub': user.username, 'scopes': ['post:delete']},
                                expires_delta=timedelta(minutes=5))
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.delete(
        url=f'posts/delete/{post_for_delete.id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'Post can be deleted/updated only by staff users or by its owner'}


@pytest.mark.anyio
async def test_delete_post_by_staff_users(client: AsyncClient,
                                          create_posts_for_user: list[Post],
                                          create_multiple_users: list[User],
                                          db: AsyncSession) -> None:
    """
    Test delete post if user has appropriate authorization scope, and it is a staff user.
    """
    staff_user = create_multiple_users[0]
    post_for_delete = create_posts_for_user[1]
    # change user role to `moderator`
    await db.execute(
        update(User.__table__)
        .where(User.id == staff_user.id)
        .values(**{'role': 'moderator'})
    )
    await db.commit()
    # get updated staff user
    buffered_staff_user = await db.execute(
        select(User)
        .where(User.id == staff_user.id)
    )

    staff_user = buffered_staff_user.scalar()
    await db.refresh(staff_user)

    # token with appropriate scope for staff user
    token = create_access_token(data={'sub': staff_user.username, 'scopes': ['post:delete']},
                                expires_delta=timedelta(minutes=5))

    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.delete(
        url=f'posts/delete/{post_for_delete.id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    buffered_post = await db.execute(
        select(Post)
        .where(Post.id == post_for_delete.id)
    )
    assert buffered_post.scalar() is None


@pytest.mark.anyio
async def test_delete_post_not_by_its_owner_if_csrf_tokens_mismatch(client: AsyncClient,
                                                                    create_multiple_users: list[User],
                                                                    create_posts_for_user: list[Post]) -> None:
    """
    Test delete post if user is not the owner of this post,
    and if csrf tokens in request header and client cookies are mismatch.
    """
    post_for_delete = create_posts_for_user[1]
    # user allows to delete post, but it's not post's owner
    user = create_multiple_users[0]
    token = create_access_token(data={'sub': user.username, 'scopes': ['post:delete']},
                                expires_delta=timedelta(minutes=5))
    client.cookies.set(name='csrftoken', value='wrong_csrf_token')

    response = await client.delete(
        url=f'posts/delete/{post_for_delete.id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


@pytest.mark.anyio
async def test_create_comment_with_authorization(client: AsyncClient,
                                                 user_for_token: User,
                                                 get_token: str,
                                                 db: AsyncSession,
                                                 create_posts_for_user: list[Post]) -> None:
    """
    Test create comment for any post if user is authorized with appropriate scope.
    """
    post_for_comment = create_posts_for_user[0]
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.post(
        url=f'/posts/comments/create/{post_for_comment.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json={'body': f'Comment for post with id {post_for_comment.id}'}
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()

    buffered_comment = await db.execute(
        select(Comment)
        .where(Comment.owner == user_for_token)
        .limit(1)
    )

    comment = buffered_comment.scalar()

    assert comment is not None
    assert response_data['likes'] == []
    assert response_data['dislikes'] == []
    assert response_data['body'] == f'Comment for post with id {post_for_comment.id}'


@pytest.mark.anyio
async def test_create_comment_without_particular_scopes(client: AsyncClient,
                                                        create_posts_for_user: list[Post],
                                                        create_multiple_users: list[User]) -> None:
    """
    Test create comment if user has not appropriate permission scope to do this.
    """
    post_for_comment = create_posts_for_user[0]
    # create token without permissions, that allow to create comment
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    response = await client.post(
        url=f'/posts/comments/create/{post_for_comment.id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json={'body': f'Comment for post with id {post_for_comment.id}'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


@pytest.mark.anyio
async def test_create_comment_if_post_does_not_exist(client: AsyncClient, get_token: str) -> None:
    """
    Test create comment if post with passed id does not exist.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    response = await client.post(
        url='/posts/comments/create/150',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json={'body': 'Comment for post with id 150}'}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Post with passed id does not exists'}


@pytest.mark.anyio
async def test_create_comment_if_csrf_tokens_mismatch(client: AsyncClient,
                                                      create_posts_for_user: list[Post],
                                                      create_multiple_users: list[User]) -> None:
    """
    Test create comment if csrf tokens in request header and client cookies are mismatch.
    """
    post_for_comment = create_posts_for_user[0]
    # create token without permissions, that allow to create comment
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    client.cookies.set(name='csrftoken', value='wrong_csrf_token')
    response = await client.post(
        url=f'/posts/comments/create/{post_for_comment.id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json={'body': f'Comment for post with id {post_for_comment.id}'}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


@pytest.mark.anyio
async def test_set_comment_like_or_dislike_with_particular_scope(client: AsyncClient,
                                                                 get_token: str,
                                                                 create_comments_to_posts_for_user: list[Comment]
                                                                 ) -> None:
    """
    Test set like or dislike for comment with comment_id.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    comment_for_set = create_comments_to_posts_for_user[1]
    # set like
    response = await client.post(
        url=f'/posts/comments/like/{comment_for_set.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['likes']) == 1  # like must be installed
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set like again
    response = await client.post(
        url=f'/posts/comments/like/{comment_for_set.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['likes']) == 0  # like must be reset
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set dislike
    response = await client.post(
        url=f'/posts/comments/dislike/{comment_for_set.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['dislikes']) == 1  # dislike must be installed
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set dislike again
    response = await client.post(
        url=f'/posts/comments/dislike/{comment_for_set.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['dislikes']) == 0  # dislike must be reset
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set like
    response = await client.post(
        url=f'/posts/comments/like/{comment_for_set.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['likes']) == 1  # like must be installed
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set dislike
    response = await client.post(
        url=f'/posts/comments/dislike/{comment_for_set.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['dislikes']) == 1  # dislike must be installed instead of like
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set like
    response = await client.post(
        url=f'/posts/comments/like/{comment_for_set.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['likes']) == 1  # like must be installed instead of dislike
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)


@pytest.mark.anyio
async def test_set_comment_like_or_dislike_if_post_does_not_exist(client: AsyncClient, get_token: str) -> None:
    """
    Test set like or dislike if passed comment does not exist by its id.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.post(
        url='/posts/comments/like/155',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Comment with passed id does not exists'}


@pytest.mark.anyio
async def test_set_comment_like_or_dislike_if_csrf_tokens_mismatch(client: AsyncClient,
                                                                   get_token: str,
                                                                   create_comments_to_posts_for_user: list[
                                                                       Comment]) -> None:
    """
    Test set like or dislike for comment with comment_id,
    if csrf tokens in request header and client cookies are mismatch.
    """
    client.cookies.set(name='csrftoken', value='wrong_csrf_token')
    comment_for_set = create_comments_to_posts_for_user[1]
    # set like
    response = await client.post(
        url=f'/posts/comments/like/{comment_for_set.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


@pytest.mark.anyio
async def test_update_comment_with_particular_scope(client: AsyncClient,
                                                    create_comments_to_posts_for_user: list[Comment],
                                                    get_token: str) -> None:
    """
    Test update comment with passed comment_id if user has appropriate scope,
    and user is owner of that comment.
    """
    # this comment was posted by user from `get_token` token data
    comment_for_update = create_comments_to_posts_for_user[1]
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.put(
        url=f'/posts/comments/update/{comment_for_update.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json={'body': f'Comment body2 for post {comment_for_update.id} updated!'}
    )

    assert response.status_code == status.HTTP_200_OK
    assert CommentShow(**jsonable_encoder(comment_for_update)) == CommentShow(**response.json())


@pytest.mark.anyio
async def test_update_comment_if_user_is_staff(client: AsyncClient,
                                               create_comments_to_posts_for_user: list[Comment],
                                               create_multiple_users: list[User],
                                               db: AsyncSession):
    """
    Test update comment with passed comment_id if user has appropriate scope,
    and user is a staff user.
    """
    staff_user = create_multiple_users[0]
    comment_for_update = create_comments_to_posts_for_user[1]
    # change user role to `moderator`
    await db.execute(
        update(User.__table__)
        .where(User.id == staff_user.id)
        .values(**{'role': 'moderator'})
    )
    await db.commit()

    # get updated staff user
    buffered_staff_user = await db.execute(
        select(User)
        .where(User.id == staff_user.id)
    )

    staff_user = buffered_staff_user.scalar()
    await db.refresh(staff_user)

    # token with appropriate scope for staff user
    token = create_access_token(data={'sub': staff_user.username, 'scopes': ['comment:update']},
                                expires_delta=timedelta(minutes=5))

    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)
    response = await client.put(
        url=f'/posts/comments/update/{comment_for_update.id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json={'body': f'Comment body2 for post {comment_for_update.id} updated!'}
    )

    assert response.status_code == status.HTTP_200_OK
    assert CommentShow(**jsonable_encoder(comment_for_update)) == CommentShow(**response.json())


@pytest.mark.anyio
async def test_update_comment_if_user_is_not_staff_or_owner(client: AsyncClient,
                                                            create_comments_to_posts_for_user: list[Comment],
                                                            create_multiple_users: list[User],
                                                            get_token: str,
                                                            db: AsyncSession) -> None:
    """
    Test update comment with passed `comment_id` if user has appropriate scope,
    but user is not a staff or is not owner.
    """
    # if user is not owner
    comment_for_update = create_comments_to_posts_for_user[1]
    new_comment_owner = create_multiple_users[0]
    user_for_update_comment = create_multiple_users[1]
    # change owner for comment
    await db.execute(
        update(Comment.__table__)
        .where(Comment.id == comment_for_update.id)
        .values(**{'owner_id': new_comment_owner.id})
    )
    await db.commit()
    await db.refresh(comment_for_update)

    # token with appropriate scope for user who will update comment
    token = create_access_token(data={'sub': user_for_update_comment.username, 'scopes': ['comment:update']},
                                expires_delta=timedelta(minutes=5))

    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.put(
        url=f'/posts/comments/update/{comment_for_update.id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json={'body': f'Comment body2 for post {comment_for_update.id} updated!'}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'Comment can be deleted/updated only by staff users or by its owner'}

    #  if user is not staff
    response = await client.put(
        url=f'/posts/comments/update/{comment_for_update.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json={'body': f'Comment body2 for post {comment_for_update.id} updated!'}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'Comment can be deleted/updated only by staff users or by its owner'}


@pytest.mark.anyio
async def test_update_comment_without_particular_scope(client: AsyncClient,
                                                       create_comments_to_posts_for_user: list[Comment],
                                                       create_multiple_users: list[User]) -> None:
    """
    Test update comment with passed comment_id,
    if user has not particular access scope for that action.
    """
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    # this comment was posted by user from `get_token` token data
    comment_for_update = create_comments_to_posts_for_user[1]
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.put(
        url=f'/posts/comments/update/{comment_for_update.id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json={'body': f'Comment body2 for post {comment_for_update.id} updated!'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


@pytest.mark.anyio
async def test_update_comment_if_passed_wrong_comment_id(client: AsyncClient, get_token: str) -> None:
    """
    Test update comment with passed wrong comment_id which does not exist in the db.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.put(
        url='/posts/comments/update/150',  # 150 is not existing id
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        },
        json={'body': 'Comment body2 for post 150 updated!'}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Comment with passed id does not exists'}


@pytest.mark.anyio
async def test_update_comment_if_csrf_tokens_mismatch(client: AsyncClient,
                                                      create_comments_to_posts_for_user: list[Comment],
                                                      get_token: str) -> None:
    """
    Test update comment with passed comment_id if csrf tokens in request header and client cookies are mismatch.
    """
    # this comment was posted by user from `get_token` token data
    comment_for_update = create_comments_to_posts_for_user[1]
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.put(
        url=f'/posts/comments/update/{comment_for_update.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': 'wrong_csrf_token'
        },
        json={'body': f'Comment body2 for post {comment_for_update.id} updated!'}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}


@pytest.mark.anyio
async def test_delete_comment_with_particular_scope(client: AsyncClient,
                                                    get_token: str,
                                                    create_comments_to_posts_for_user: list[Comment],
                                                    db: AsyncSession) -> None:
    """
    Test delete comment by its id if user has appropriate access scope for this action.
    """
    comment_for_delete = create_comments_to_posts_for_user[0]
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.delete(
        url=f'posts/comments/delete/{comment_for_delete.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    buffered_comment = await db.execute(
        select(Comment)
        .where(Comment.id == comment_for_delete.id)
    )
    assert buffered_comment.scalar() is None


@pytest.mark.anyio
async def test_delete_comment_if_passed_wrong_comment_id(client: AsyncClient, get_token: str) -> None:
    """
    Test delete comment by its id if passed id does not matched with any comment.
    """
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.delete(
        url='posts/comments/delete/150',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Comment with passed id does not exists'}


@pytest.mark.anyio
async def test_delete_comment_if_user_not_owner_or_staff(client: AsyncClient,
                                                         get_token: str,
                                                         create_comments_to_posts_for_user: list[Comment],
                                                         create_multiple_users: list[User],
                                                         db: AsyncSession) -> None:
    """
    Test delete comment by its id if user is not staff or is not comment's owner.
    """
    # if user is not owner
    comment_for_delete = create_comments_to_posts_for_user[1]
    old_comment_owner = comment_for_delete.owner
    new_comment_owner = create_multiple_users[1]
    # change owner for comment for delete
    await db.execute(
        update(Comment.__table__)
        .where(Comment.id == comment_for_delete.id)
        .values(**{'owner_id': new_comment_owner.id})
    )
    await db.commit()
    await db.refresh(comment_for_delete)

    token = create_access_token(data={'sub': old_comment_owner.username, 'scopes': ['comment:delete']},
                                expires_delta=timedelta(minutes=5))

    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.delete(
        url=f'posts/comments/delete/{comment_for_delete.id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'Comment can be deleted/updated only by staff users or by its owner'}

    # if user is not staff
    response = await client.delete(
        url=f'posts/comments/delete/{comment_for_delete.id}',
        headers={
            'Authorization': f'Bearer {get_token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'Comment can be deleted/updated only by staff users or by its owner'}


@pytest.mark.anyio
async def test_delete_comment_without_particular_scope(client: AsyncClient,
                                                       create_comments_to_posts_for_user: list[Comment],
                                                       create_multiple_users: list[User]) -> None:
    """
    Test delete comment by its id if user has not appropriate scope to do this action.
    """
    # token without access scope for delete comment
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    comment_for_delete = create_comments_to_posts_for_user[1]
    client.cookies.set(name='csrftoken', value=TEST_CSRF_TOKEN)

    response = await client.delete(
        url=f'posts/comments/delete/{comment_for_delete.id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


@pytest.mark.anyio
async def test_delete_comment_if_csrf_tokens_mismatch(client: AsyncClient,
                                                      create_comments_to_posts_for_user: list[Comment],
                                                      create_multiple_users: list[User]) -> None:
    """
    Test delete comment by its id if csrf tokens in request header and client cookies are mismatch.
    """
    # token without access scope for delete comment
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    comment_for_delete = create_comments_to_posts_for_user[1]
    client.cookies.set(name='csrftoken', value='wrong_csrf_token')

    response = await client.delete(
        url=f'posts/comments/delete/{comment_for_delete.id}',
        headers={
            'Authorization': f'Bearer {token}',
            'X-CSRFToken': TEST_CSRF_TOKEN
        }
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'CSRF token missing or incorrect'}
