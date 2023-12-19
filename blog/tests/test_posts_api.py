from fastapi import status
from fastapi.encoders import jsonable_encoder

from accounts.schemas import UserShowBriefly
from accounts.security import get_token_data
from posts.schemas import (
    PostShow, PostUpdate,
    CategoryCreate, CommentShow,
    Category as CategorySchema
)
from .fixtures import *

POST_DATA = {
    'title': 'Post title 1',
    'body': 'Post body',
    'tags': ['tag1', 'tag2']
}


def test_create_post_with_authorization(client: TestClient,
                                        create_post_category: Category,
                                        get_token: str,
                                        db: Session) -> None:
    """
    Test create post behalf current authenticated user.
    """
    POST_DATA.update(category=create_post_category.name)
    response = client.post(
        url='/posts/create',
        json=POST_DATA,
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    created_post = db.get(Post, response_data['id'])
    created_post_dict = jsonable_encoder(created_post)
    created_post_dict.update(
        tags=created_post.tags.split(','),
        owner=UserShowBriefly(id=created_post.owner_id, username=created_post.owner.username),
        category=CategoryCreate(name=created_post.category.name)
    )
    assert PostShow(**response_data) == PostShow(**created_post_dict)


def test_create_post_without_authentication(client: TestClient,
                                            create_post_category: Category,
                                            user_for_token: User) -> None:
    """
    Test create post without authentication.
    """
    POST_DATA.update(category=create_post_category.name,
                     owner=user_for_token.username)
    response = client.post(
        url='/posts/create',
        json=POST_DATA
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not authenticated'}


def test_create_post_without_particular_scopes(client: TestClient,
                                               create_post_category: Category,
                                               create_multiple_users: list[User]) -> None:
    """
    Test create post without particular scope for endpoint.
    """
    POST_DATA.update(category=create_post_category.name,
                     owner=create_multiple_users[0].username)
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    response = client.post(
        url='/posts/create',
        json=POST_DATA,
        # token without particular scope
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_create_category_with_authorization(client: TestClient, get_token: str) -> None:
    """
    Test create category for posts.
    """
    response = client.post(
        url='/posts/category/create',
        headers={'Authorization': f'Bearer {get_token}'},
        json={'name': 'Computers'}
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()['name'] == 'Computers'


def test_create_category_without_authentication(client: TestClient) -> None:
    """
    Test create category for posts without authentication.
    """
    response = client.post(
        url='/posts/category/create',
        json={'name': 'Computers'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not authenticated'}


def test_create_category_without_particular_scopes(client: TestClient, create_multiple_users: list[User]) -> None:
    """
    Test create category for posts without authorization with appropriate scope
    """
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    response = client.post(
        url='/posts/category/create',
        json={'name': 'Computers'},
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_read_post(client: TestClient, create_posts_for_user: list[Post]) -> None:
    """
    Test read post by its id.
    """
    post_for_receiving = create_posts_for_user[1]
    response = client.get(url=f'posts/read/{post_for_receiving.id}')

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    post_data_dict = jsonable_encoder(post_for_receiving)
    post_data_dict.update(
        tags=post_for_receiving.tags.split(','),
        owner=UserShowBriefly(id=post_for_receiving.owner_id, username=post_for_receiving.owner.username),
        category=CategoryCreate(name=post_for_receiving.category.name)
    )
    assert PostShow(**response_data) == PostShow(**post_data_dict)


def test_read_posts(client: TestClient, create_posts_for_user: list[Post]) -> None:
    """
    Test read all posts in the database.
    """
    post_for_receiving1 = create_posts_for_user[0]
    post_for_receiving2 = create_posts_for_user[1]
    response = client.get(url='posts/read_all/posts')

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data) == 2
    post1_data = jsonable_encoder(post_for_receiving1)
    post2_data = jsonable_encoder(post_for_receiving2)
    post1_data.update(
        tags=post_for_receiving1.tags.split(','),
        owner=UserShowBriefly(id=post_for_receiving1.owner_id, username=post_for_receiving1.owner.username),
        category=CategoryCreate(name=post_for_receiving1.category.name)
    )
    post2_data.update(
        tags=post_for_receiving2.tags.split(','),
        owner=UserShowBriefly(id=post_for_receiving2.owner_id, username=post_for_receiving2.owner.username),
        category=CategoryCreate(name=post_for_receiving2.category.name)
    )
    assert PostShow(**response_data[0]) == PostShow(**post1_data)
    assert PostShow(**response_data[1]) == PostShow(**post2_data)


def test_read_post_categories(client: TestClient, create_post_category: Category) -> None:
    """
    Test read all posts categories.
    """
    response = client.get(url='/posts/read_all/categories')
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data) == 1
    assert CategorySchema(**jsonable_encoder(create_post_category)) == CategorySchema(**response_data[0])


def test_update_post_with_authorization(client: TestClient,
                                        create_posts_for_user: list[Post],
                                        get_token: str) -> None:
    """
    Update post by passed post_id with corresponding authorization scope.
    """
    post_for_update = create_posts_for_user[0]
    post_data = jsonable_encoder(post_for_update)
    post_data.update(rating=4,
                     body='post_body_updated',
                     tags=post_data['tags'].split(','),
                     category=post_for_update.category.name)
    post_update_body = PostUpdate(**post_data)
    response = client.put(
        url=f'/posts/update/{post_for_update.id}',
        headers={'Authorization': f'Bearer {get_token}'},
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


def test_update_post_without_authentication(client: TestClient,
                                            create_posts_for_user: list[Post]) -> None:
    """
    Update post by passed post_id without authentication.
    """
    post_for_update = create_posts_for_user[0]
    post_data = jsonable_encoder(post_for_update)
    post_data.update(rating=4,
                     body='post_body_updated',
                     tags=post_data['tags'].split(','),
                     category=post_for_update.category.name)
    post_update_body = PostUpdate(**post_data)
    response = client.put(
        url=f'/posts/update/{post_for_update.id}',
        json=post_update_body.model_dump()
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not authenticated'}


def test_delete_post_with_authorization(client: TestClient,
                                        get_token: str,
                                        create_posts_for_user: list[Post],
                                        db: Session):
    """
    Test delete post if user has appropriate authorization scope, and it is a post's owner.
    """
    post_for_delete = create_posts_for_user[1]
    response = client.delete(
        url=f'posts/delete/{post_for_delete.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert db.get(Post, post_for_delete.id) is None


def test_delete_post_not_by_its_owner(client: TestClient,
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
    response = client.delete(
        url=f'posts/delete/{post_for_delete.id}',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'Post can be updated only by staff users or by its owner'}


def test_delete_post_by_staff_users(client: TestClient,
                                    get_token: str,
                                    create_posts_for_user: list[Post],
                                    db: Session) -> None:
    """
    Test delete post if user has appropriate authorization scope, and it is a staff user.
    """
    # get username from access token, find it in the db and update its role
    username_from_token = get_token_data(get_token).username
    db.query(User).filter(User.username == username_from_token).update({'role': 'moderator'})

    post_for_delete = create_posts_for_user[1]
    response = client.delete(
        url=f'posts/delete/{post_for_delete.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert db.get(Post, post_for_delete.id) is None


def test_create_comment_with_authorization(client: TestClient,
                                           get_token: str,
                                           db: Session,
                                           create_posts_for_user: list[Post]) -> None:
    """
    Test create comment for any post if user is authorized with appropriate scope.
    """
    post_for_comment = create_posts_for_user[0]
    response = client.post(
        url=f'/posts/create_comment/{post_for_comment.id}',
        headers={'Authorization': f'Bearer {get_token}'},
        json={'body': f'Comment for post with id {post_for_comment.id}'}
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    username_from_token = get_token_data(get_token).username
    user = db.query(User).filter(User.username == username_from_token).first()
    assert post_for_comment.owner == user
    assert response_data['likes'] == []
    assert response_data['dislikes'] == []
    assert response_data['body'] == f'Comment for post with id {post_for_comment.id}'


def test_create_comment_without_particular_scopes(client: TestClient,
                                                  create_posts_for_user: list[Post],
                                                  create_multiple_users: list[User]) -> None:
    """
    Test create comment if user has not appropriate permission scope to do this.
    """
    post_for_comment = create_posts_for_user[0]
    # create token without permissions, that allow to create comment
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    response = client.post(
        url=f'/posts/create_comment/{post_for_comment.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={'body': f'Comment for post with id {post_for_comment.id}'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_create_comment_if_post_does_not_exist(client: TestClient, get_token: str) -> None:
    """
    Test create comment if post with passed id does not exist.
    """
    response = client.post(
        url='/posts/create_comment/150',
        headers={'Authorization': f'Bearer {get_token}'},
        json={'body': 'Comment for post with id 150}'}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Post with passed id does not exists'}


def test_set_comment_like_or_dislike_with_particular_scope(client: TestClient,
                                                           get_token: str,
                                                           create_comments_for_user: list[Comment]) -> None:
    """
    Test set like or dislike for comment with comment_id.
    """
    comment_for_set = create_comments_for_user[1]
    # set like
    response = client.post(
        url=f'/posts/comment/like/{comment_for_set.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['likes']) == 1  # like must be installed
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set like again
    response = client.post(
        url=f'/posts/comment/like/{comment_for_set.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['likes']) == 0  # like must be reset
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set dislike
    response = client.post(
        url=f'/posts/comment/dislike/{comment_for_set.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['dislikes']) == 1  # dislike must be installed
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set dislike again
    response = client.post(
        url=f'/posts/comment/dislike/{comment_for_set.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['dislikes']) == 0  # dislike must be reset
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set like
    response = client.post(
        url=f'/posts/comment/like/{comment_for_set.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['likes']) == 1  # like must be installed
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set dislike
    response = client.post(
        url=f'/posts/comment/dislike/{comment_for_set.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['dislikes']) == 1  # dislike must be installed instead of like
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)

    # set like
    response = client.post(
        url=f'/posts/comment/like/{comment_for_set.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data['likes']) == 1  # like must be installed instead of dislike
    assert CommentShow(**jsonable_encoder(comment_for_set)) == CommentShow(**response_data)


def test_set_comment_like_or_dislike_if_post_does_not_exist(client: TestClient, get_token: str) -> None:
    """
    Test set like or dislike if passed comment does not exist by its id.
    """
    response = client.post(
        url='/posts/comment/like/155',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Comment with passed id does not exists'}


def test_set_comment_like_or_dislike_if_passed_wrong_command(client: TestClient,
                                                             get_token: str,
                                                             create_comments_for_user: list[Comment]) -> None:
    """
    Test set like or dislike if passed neither like nor dislike as action.
    """
    comment_for_set = create_comments_for_user[1]
    response = client.post(
        # will pass `wrong` command instead of either `like` or `dislike`
        url=f'/posts/comment/wrong/{comment_for_set.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail': 'Action is either like or dislike. Action <wrong> was passed'}


def test_update_comment_with_particular_scope(client: TestClient,
                                              create_comments_for_user: list[Comment],
                                              get_token: str) -> None:
    """
    Test update comment with passed comment_id if user has appropriate scope,
    and user is owner of that comment.
    """
    # this comment was posted by user from `get_token` token data
    comment_for_update = create_comments_for_user[1]
    response = client.put(
        url=f'/posts/comment/update/{comment_for_update.id}',
        headers={'Authorization': f'Bearer {get_token}'},
        json={'body': f'Comment body2 for post {comment_for_update.id} updated!'}
    )

    assert response.status_code == status.HTTP_200_OK
    assert CommentShow(**jsonable_encoder(comment_for_update)) == CommentShow(**response.json())


def test_update_comment_if_user_is_staff(client: TestClient,
                                         create_comments_for_user: list[Comment],
                                         get_token: str,
                                         db: Session):
    """
    Test update comment with passed comment_id if user has appropriate scope,
    and user is a staff user.
    """
    # get username from access token, find it in the db and update its role
    username_from_token = get_token_data(get_token).username
    db.query(User).filter(User.username == username_from_token).update({'role': 'moderator'})
    # this comment was posted by user from `get_token` token data
    comment_for_update = create_comments_for_user[1]
    response = client.put(
        url=f'/posts/comment/update/{comment_for_update.id}',
        headers={'Authorization': f'Bearer {get_token}'},
        json={'body': f'Comment body2 for post {comment_for_update.id} updated!'}
    )

    assert response.status_code == status.HTTP_200_OK
    assert CommentShow(**jsonable_encoder(comment_for_update)) == CommentShow(**response.json())


def test_update_comment_if_user_is_not_staff_or_owner(client: TestClient,
                                                      create_comments_for_user: list[Comment],
                                                      create_multiple_users: list[User],
                                                      get_token: str,
                                                      db: Session) -> None:
    """
    Test update comment with passed comment_id if user has appropriate scope,
    but user not a staff.
    """
    comment_for_update = create_comments_for_user[1]
    # change owner for comment
    db.query(Comment).update({'owner_id': create_multiple_users[1].id})
    create_comments_for_user[1].owner = create_multiple_users[1]

    response = client.put(
        url=f'/posts/comment/update/{comment_for_update.id}',
        headers={'Authorization': f'Bearer {get_token}'},
        json={'body': f'Comment body2 for post {comment_for_update.id} updated!'}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'Comment can be updated only by staff users or by its owner'}

    # owner is not staff user
    response = client.put(
        url=f'/posts/comment/update/{comment_for_update.id}',
        headers={'Authorization': f'Bearer {get_token}'},
        json={'body': f'Comment body2 for post {comment_for_update.id} updated!'}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'Comment can be updated only by staff users or by its owner'}


def test_update_comment_without_particular_scope(client: TestClient,
                                                 create_comments_for_user: list[Comment],
                                                 create_multiple_users: list[User]) -> None:
    """
    Test update comment with passed comment_id,
    if user has not particular access scope for that action.
    """
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    # this comment was posted by user from `get_token` token data
    comment_for_update = create_comments_for_user[1]
    response = client.put(
        url=f'/posts/comment/update/{comment_for_update.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={'body': f'Comment body2 for post {comment_for_update.id} updated!'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}


def test_update_comment_if_passed_wrong_comment_id(client: TestClient, get_token: str) -> None:
    """
    Test update comment with passed wrong comment_id which does not exist in the db.
    """
    response = client.put(
        url='/posts/comment/update/150',  # 150 is not existing id
        headers={'Authorization': f'Bearer {get_token}'},
        json={'body': 'Comment body2 for post 150 updated!'}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Comment with passed id does not exists'}


def test_delete_comment_with_particular_scope(client: TestClient,
                                              get_token: str,
                                              create_comments_for_user: list[Comment],
                                              db: Session) -> None:
    """
    Test delete comment by its id if user has appropriate access scope for this action.
    """
    comment_for_delete = create_comments_for_user[0]
    response = client.delete(
        url=f'posts/comment/delete/{comment_for_delete.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert db.get(Comment, comment_for_delete.id) is None


def test_delete_comment_if_passed_wrong_comment_id(client: TestClient, get_token: str) -> None:
    """
    Test delete comment by its id if passed id does not matched with any comment.
    """
    response = client.delete(
        url='posts/comment/delete/150',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail': 'Comment with passed id does not exists'}


def test_delete_comment_if_user_not_owner_or_staff(client: TestClient,
                                                   get_token: str,
                                                   create_comments_for_user: list[Comment],
                                                   create_multiple_users: list[User],
                                                   db: Session) -> None:
    """
    Test delete comment by its id if user not staff or comment's owner.
    """
    comment_for_delete = create_comments_for_user[1]
    # change owner for comment for delete
    db.query(Comment).filter(Comment.id == comment_for_delete.id).update({'owner_id': create_multiple_users[1].id})
    create_comments_for_user[1].owner = create_multiple_users[1]
    response = client.delete(
        url=f'posts/comment/delete/{comment_for_delete.id}',
        headers={'Authorization': f'Bearer {get_token}'}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {'detail': 'Comment can be updated only by staff users or by its owner'}


def test_delete_comment_without_particular_scope(client: TestClient,
                                                 create_comments_for_user: list[Comment],
                                                 create_multiple_users: list[User]) -> None:
    """
    Test delete comment by its id if user has not appropriate scope to do this action.
    """
    # token without access scope for delete comment
    token = create_access_token(data={'sub': create_multiple_users[0].username, 'scopes': ['random:scope']},
                                expires_delta=timedelta(minutes=5))
    comment_for_delete = create_comments_for_user[1]
    response = client.delete(
        url=f'posts/comment/delete/{comment_for_delete.id}',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {'detail': 'Not enough permissions'}
