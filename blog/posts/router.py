import logging
from typing import Literal, Type, Annotated, Union

from fastapi import (
    APIRouter, status, HTTPException,
    Query, Security
)
from fastapi.encoders import jsonable_encoder
from fastapi_cache.decorator import cache

from common.crud_operations import CrudManagerAsync
from common.utils import show_exception, PickleCoderRedis
from config import get_settings
from dependencies import (
    DatabaseDependency,
    get_current_user,
    SecurityScopesDependency,
    CsrfVerifyDependency
)
from loggers.logs_config import (
    set_endpoint_logger,
    FORMATTER_FORMAT,
    FORMATTER_DATA_FORMAT,
)
from posts import schemas, models, crud
from posts.utils import create_post_show_instance_with_extra_attributes, is_object_owner_or_staff_user
from settings import env_dirs

settings = get_settings()

endpoints_logger = logging.getLogger(__name__)
endpoints_formatter = logging.Formatter(fmt=FORMATTER_FORMAT, datefmt=FORMATTER_DATA_FORMAT)
endpoint_handler = logging.FileHandler(filename=f'{env_dirs.LOGS_DIRECTORY}/posts_endpoints.log', encoding='utf-8')
endpoint_handler.setFormatter(endpoints_formatter)
endpoints_logger.addHandler(endpoint_handler)

router = APIRouter()


@router.post('/create',
             response_model=schemas.PostShow,
             status_code=status.HTTP_201_CREATED,
             summary='Create Post',
             operation_id='create-post',
             dependencies=[CsrfVerifyDependency],
             responses={
                 404: {'detail': 'Post category is not found'},
                 400: {'detail': 'Post is already exists'},
                 401: {'detail': 'Not enough permissions'}}
             )
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/create')
async def create_post(current_user: SecurityScopesDependency(scopes=['post:create']),
                      post: schemas.PostCreate,
                      db: DatabaseDependency) -> Union[schemas.PostShow, HTTPException]:
    """
    Create `post` behalf `current_user`.
    """
    crud_manager_post = CrudManagerAsync(db, models.Post)
    crud_manager_category = CrudManagerAsync(db, models.Category)
    # check if post category with passed name exists
    db_category = await crud_manager_category.retrieve(models.Category.name == post.category)
    if db_category is None:
        raise show_exception('category', status.HTTP_404_NOT_FOUND)
    # check if post with passed title not exists
    db_post = await crud_manager_post.retrieve(models.Post.title == post.title)
    if db_post:
        raise show_exception('post', status.HTTP_400_BAD_REQUEST)
    data_for_post_show: dict = {}
    # get created post, encode it into JSON, excluding post's tags, owner, category to avoid recursion exceeded limit
    # instantiate other schemas which are in `PostShow` schema
    # fill data for `PostShow` instance and create it from that data
    created_post = await crud_manager_post.create({
        'title': post.title,
        'body': post.body,
        'tags': post.tags,
        'category_id': db_category.id,
        'owner_id': current_user.id
    })
    post_info = jsonable_encoder(created_post, exclude={'tags', 'owner', 'category'})
    category = schemas.CategoryCreate(name=post.category)
    owner = schemas.UserShowBriefly(id=created_post.owner_id, username=created_post.owner.username)
    data_for_post_show.update(category=category,
                              count_comments=0,
                              owner=owner,
                              tags=created_post.tags,
                              **post_info)
    post_show = schemas.PostShow(**data_for_post_show)
    return post_show


@router.post('/categories/create',
             response_model=schemas.CategoryCreate,
             status_code=status.HTTP_201_CREATED,
             operation_id='create-post-category',
             summary='Create Post Category',
             dependencies=[Security(get_current_user, scopes=['category:create']), CsrfVerifyDependency],
             responses={
                 400: {'detail': 'Category is already exists'},
                 401: {'detail': 'Not enough permissions'}}
             )
async def create_category(category: schemas.CategoryCreate,
                          db: DatabaseDependency) -> Union[models.Category, HTTPException]:
    """
    Create post's `category`.
    """
    crud_manager = CrudManagerAsync(db, models.Category)
    db_category = await crud_manager.retrieve(models.Category.name == category.name)
    if db_category:
        raise show_exception('category', status.HTTP_400_BAD_REQUEST)
    return await crud_manager.create(jsonable_encoder(category))


@router.get('/read/{post_id}',
            response_model=schemas.PostShow,
            status_code=status.HTTP_200_OK,
            operation_id='get-post-by-id',
            summary='Get Post By Passed `post_id`',
            responses={404: {'detail': 'Post is not found'}})
@cache(expire=300, namespace=models.Post.__tablename__)
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/read/{post_id}')
async def read_post(db: DatabaseDependency, post_id: int) -> schemas.PostShow:
    """
    Obtain post by its `post_id`.
    """
    query = await crud.get_post_by_id_query(post_id)
    buffered_post = await db.execute(query)
    post = buffered_post.mappings().first()
    if post is None:
        raise show_exception('post', status.HTTP_404_NOT_FOUND)
    return create_post_show_instance_with_extra_attributes(post)


@router.get('/posts/read_all',
            response_model=list[schemas.PostShow],
            status_code=status.HTTP_200_OK,
            operation_id='get-all-posts',
            summary='Get All Posts')
@cache(expire=300, namespace=models.Post.__tablename__)
async def read_posts(db: DatabaseDependency,
                     category: Annotated[str, Query(description='Post category')] = '',
                     skip: int = 0,
                     limit: int = 100,
                     sort_by: Annotated[Literal[
                         'created_asc',
                         'created_desc',
                         'rating_asc',
                         'rating_desc',
                         'post_comments_asc',
                         'post_comments_desc'
                     ], Query(description='Sort criteria')] = 'created_desc') -> list[schemas.PostShow]:
    """
    Obtain all posts with `skip`, `limit` and appropriate `category` if it provided.
    Sort result by `sort_by` criteria.
    """
    query = await crud.get_posts_query(category, skip, limit, sort_by)
    # rows with post's scalars values as list
    buffered_posts_rows = await db.execute(query)
    posts_rows = buffered_posts_rows.mappings()
    posts_show_list = [create_post_show_instance_with_extra_attributes(row) for row in posts_rows]

    return posts_show_list


@router.get('/categories/read_all',
            response_model=list[schemas.Category],
            status_code=status.HTTP_200_OK,
            operation_id='get-all-posts-categories',
            summary='Get All Posts Categories')
# used custom `PickleCoderRedis` coder in order to avoid `maximum recursion exceeded` error,
# while FastAPI tries to save response data to Redis Cache.
@cache(expire=300, namespace=models.Category.__tablename__, coder=PickleCoderRedis)
async def read_post_categories(db: DatabaseDependency,
                               skip: int = 0,
                               limit: int = 100) -> list[Type[models.Category]]:
    """
    Obtain all categories with `skip` and `limit`.
    """
    scalars_categories = await CrudManagerAsync(db, models.Category).retrieve(many=True, skip=skip, limit=limit)
    return scalars_categories.all()


@router.get('/categories/read/{category_id}',
            response_model=schemas.Category,
            operation_id='get-post-category-by-id',
            status_code=status.HTTP_200_OK,
            summary='Get Post Category By Passed `category_id`',
            responses={404: {'detail': 'Category is not found'}})
# used custom `PickleCoderRedis` coder in order to avoid `maximum recursion exceeded` error,
# while FastAPI tries to save response data to Redis Cache.
@cache(expire=300, namespace=models.Category.__tablename__, coder=PickleCoderRedis)
async def read_post_category(db: DatabaseDependency, category_id: int) -> Type[models.Category]:
    """
    Obtain post category by its `category_id`.
    """
    db_category = await CrudManagerAsync(db, models.Category).retrieve(models.Category.id == category_id)
    if db_category is None:
        raise show_exception('category', status.HTTP_404_NOT_FOUND)
    return db_category


@router.put('/update/{post_id}',
            response_model=schemas.PostShow,
            status_code=status.HTTP_200_OK,
            operation_id='update-post-by-id',
            summary='Update Post By Passed `post_id`',
            dependencies=[CsrfVerifyDependency],
            responses={
                404: {'detail': 'Post is not found'},
                403: {'detail': 'Updating post not by staff user or not by post owner'},
                401: {'detail': 'Not enough permissions'}}
            )
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/update/{post_id}')
async def update_post(post_id: int,
                      data: schemas.PostUpdate,
                      current_user: SecurityScopesDependency(scopes=['post:update']),
                      db: DatabaseDependency) -> Union[schemas.PostShow, HTTPException]:
    """
    Update post's data.
    """
    query = await crud.get_post_by_id_query(post_id)
    post_row_mapping = await db.execute(query)
    db_post = post_row_mapping.scalar()
    if not db_post:
        raise show_exception('post', status.HTTP_404_NOT_FOUND)
    # restriction update post only by staff users or post's owner,
    # even `current_user` has appropriate authorization scope
    if not is_object_owner_or_staff_user(db_post, current_user):
        raise show_exception('post', status.HTTP_403_FORBIDDEN)
    data_to_update = data.model_dump(exclude={'id', 'category'})
    data_to_update.update({
        'category_id': db_post.category_id,
        'tags': data_to_update['tags']
    })
    post_data_dict = jsonable_encoder(data_to_update)
    updated_post = await CrudManagerAsync(db, models.Post).update(db_post, post_data_dict)
    post_show = create_post_show_instance_with_extra_attributes(updated_post)
    return post_show


@router.delete('/delete/{post_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               operation_id='delete-post-by-id',
               summary='Delete Post By Passed `post_id`',
               dependencies=[CsrfVerifyDependency],
               responses={
                   404: {'detail': 'Post is not found'},
                   403: {'detail': 'Removing post not by staff user or not by post owner'},
                   401: {'detail': 'Not enough permissions'}}
               )
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/delete/{post_id}')
async def delete_post(db: DatabaseDependency,
                      current_user: SecurityScopesDependency(scopes=['post:delete']),
                      post_id: int) -> None:
    """
    Remove post by its `post_id`.
    """
    query = await crud.get_post_by_id_query(post_id)
    buffered_db_post = await db.execute(query)
    db_post = buffered_db_post.scalar()
    if not db_post:
        raise show_exception('post', status.HTTP_404_NOT_FOUND)
    # post can be deleted only by its owner or staff users
    if not is_object_owner_or_staff_user(db_post, current_user):
        raise show_exception('post', status.HTTP_403_FORBIDDEN)

    await CrudManagerAsync(db, models.Post).destroy(db_post)


@router.post('/comments/create/{post_id}',
             response_model=schemas.CommentShow,
             status_code=status.HTTP_201_CREATED,
             operation_id='create-post-comment-by-post-id',
             summary='Create Comment For Post With `post_id`',
             dependencies=[CsrfVerifyDependency],
             responses={
                 404: {'detail': 'Post is not found'},
                 401: {'detail': 'Not enough permissions'}}
             )
async def create_comment(db: DatabaseDependency,
                         current_user: SecurityScopesDependency(scopes=['comment:create']),
                         comment: schemas.CommentCreateOrUpdate,
                         post_id: int) -> models.Comment:
    """
    Create comment for post with `post_id` behalf `current_user`.
    """
    query = await crud.get_post_by_id_query(post_id)
    buffered_db_post = await db.execute(query)
    db_post = buffered_db_post.scalar()
    if not db_post:
        raise show_exception('post', status.HTTP_404_NOT_FOUND)
    return await CrudManagerAsync(db, models.Comment).create({
        'body': comment.body,
        'post_id': post_id,
        'owner_id': current_user.id
    })


@router.post('/comments/{action}/{comment_id}',
             response_model=schemas.CommentShow,
             operation_id='create-comment-status-by-comment-id',
             status_code=status.HTTP_200_OK,
             summary='Set Like Or Dislike `action` For Comment With `comment_id` Behalf Current User',
             dependencies=[CsrfVerifyDependency],
             responses={
                 404: {'detail': 'Comment not found'},
                 401: {'detail': 'Not enough permissions'}}
             )
async def set_comment_like_or_dislike(db: DatabaseDependency,
                                      current_user: SecurityScopesDependency(scopes=['comment:rate']),
                                      comment_id: int,
                                      action: Literal['like', 'dislike']) -> models.Comment:
    """
    Set like/dislike for comment with `comment_id` behalf `current_user`.
    """
    current_user = await db.merge(current_user)  # copy instance into current session `db`
    db_comment = await CrudManagerAsync(db, models.Comment).retrieve(models.Comment.id == comment_id)
    if not db_comment:
        raise show_exception('comment', status.HTTP_404_NOT_FOUND)

    if action not in ('like', 'dislike'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Action is either like or dislike. Action <{action}> was passed'
        )

    return await crud.set_like_or_dislike_for_comment(db, current_user, db_comment, action)


@router.put('/comments/update/{comment_id}',
            response_model=schemas.CommentShow,
            status_code=status.HTTP_200_OK,
            operation_id='update-comment-by-id',
            summary='Update Comment By `comment_id`',
            dependencies=[CsrfVerifyDependency],
            responses={
                400: {'detail': 'Updating comment not by staff user or not by comment owner'},
                404: {'detail': 'Comment not found'},
                401: {'detail': 'Not enough permissions'}}
            )
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/comment/update/{comment_id}')
async def update_comment(db: DatabaseDependency,
                         current_user: SecurityScopesDependency(scopes=['comment:update']),
                         data: schemas.CommentCreateOrUpdate,
                         comment_id: int) -> models.Comment:
    """
    Update comment by `comment_id`.
    """
    crud_manager = CrudManagerAsync(db, models.Comment)
    db_comment = await crud_manager.retrieve(models.Comment.id == comment_id)
    if not db_comment:
        raise show_exception('comment', status.HTTP_404_NOT_FOUND)
    # comment can be updated only by its owner or staff users
    if not is_object_owner_or_staff_user(db_comment, current_user):
        raise show_exception('comment', status.HTTP_403_FORBIDDEN)

    data_to_update = data.model_dump(exclude_none=True)
    return await crud_manager.update(db_comment, data_to_update)


@router.delete('/comments/delete/{comment_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               operation_id='delete-comment-by-id',
               summary='Delete Comment By `comment_id`',
               dependencies=[CsrfVerifyDependency],
               responses={
                   400: {'detail': 'Removing comment not by staff user or not by comment owner'},
                   404: {'detail': 'Comment not found'},
                   401: {'detail': 'Not enough permissions'}}
               )
async def remove_comment(db: DatabaseDependency,
                         current_user: SecurityScopesDependency(scopes=['comment:delete']),
                         comment_id: int) -> None:
    """
    Delete comment by passed `comment_id`.
    """
    crud_manager = CrudManagerAsync(db, models.Comment)
    db_comment = await crud_manager.retrieve(models.Comment.id == comment_id)
    if db_comment is None:
        raise show_exception('comment', status.HTTP_404_NOT_FOUND)
    if not is_object_owner_or_staff_user(db_comment, current_user):
        raise show_exception('comment', status.HTTP_403_FORBIDDEN)
    await crud_manager.destroy(db_comment)
