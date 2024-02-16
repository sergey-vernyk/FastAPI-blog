import logging
from typing import Literal, Type, Annotated, Union

from fastapi import (
    APIRouter, status, HTTPException,
    Query, Security
)
from fastapi.encoders import jsonable_encoder
from fastapi_cache.decorator import cache

from accounts.models import User
from common.crud_operations import CrudManager
from common.utils import show_exception
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
             dependencies=[CsrfVerifyDependency])
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/create')
async def create_post(current_user: Annotated[User, Security(get_current_user, scopes=['post:create'])],
                      post: schemas.PostCreate,
                      db: DatabaseDependency) -> Union[schemas.PostShow, HTTPException]:
    """
    Create `post` behalf `current_user`.
    """
    crud_manager_post, crud_manager_category = CrudManager(db, models.Post), CrudManager(db, models.Category)
    # check if post category with passed name exists
    db_category = await crud_manager_category.retrieve(models.Category.name == post.category)
    if db_category is None:
        raise show_exception('category', status.HTTP_404_NOT_FOUND)
    # check if post with passed title not exists
    db_post = await crud_manager_post.retrieve(models.Post.title == post.title)
    if db_post:
        raise show_exception('post', status.HTTP_400_BAD_REQUEST)
    data_for_post_show: dict = {}
    # get created post, encode it into JSON, excluding post's tags and owner
    # instantiate other schemas which are in `PostShow` schema
    # fill data for `PostShow` instance and create it from that data
    post = await crud_manager_post.create({
        'title': post.title,
        'body': post.body,
        'tags': post.tags,
        'category_id': db_category.id,
        'owner_id': current_user.id
    })
    post_info = jsonable_encoder(post, exclude={'tags', 'owner'})
    category = schemas.CategoryCreate(name=post.category.name)
    owner = schemas.UserShowBriefly(id=post.owner_id, username=post.owner.username)
    data_for_post_show.update(comments=[],
                              category=category,
                              count_comments=0,
                              owner=owner,
                              tags=post.tags,
                              **post_info)
    post_show = schemas.PostShow(**data_for_post_show)
    return post_show


@router.post('/category/create',
             response_model=schemas.CategoryCreate,
             status_code=status.HTTP_201_CREATED,
             summary='Create Post Category',
             dependencies=[Security(get_current_user, scopes=['category:create']), CsrfVerifyDependency])
async def create_category(category: schemas.CategoryCreate,
                          db: DatabaseDependency) -> Union[models.Category, HTTPException]:
    """
    Create post's `category`.
    """
    crud_manager = CrudManager(db, models.Category)
    db_category = await crud_manager.retrieve(models.Category.name == category.name)
    if db_category:
        raise show_exception('category', status.HTTP_400_BAD_REQUEST)
    return await crud_manager.create(jsonable_encoder(category))


@router.get('/read/{post_id}',
            response_model=schemas.PostShow,
            status_code=status.HTTP_200_OK,
            summary='Get Post By Passed `post_id`')
@cache(expire=300, namespace=models.Category.__tablename__)
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/read/{post_id}')
async def read_post(db: DatabaseDependency, post_id: int) -> schemas.PostShow:
    """
    Obtain post by its `post_id`.
    """
    query = await crud.get_post_by_id_query(post_id)
    post = db.execute(query).mappings().first()
    if not post:
        raise show_exception('post', status.HTTP_404_NOT_FOUND)
    return create_post_show_instance_with_extra_attributes(post)


@router.get('/read_all/posts',
            response_model=list[schemas.PostShow],
            status_code=status.HTTP_200_OK,
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
    """
    query = await crud.get_posts_query(category, skip, limit, sort_by)
    # rows with post's scalars values as list
    posts_rows = db.execute(query).mappings()
    posts_show_list = [create_post_show_instance_with_extra_attributes(row) for row in posts_rows]

    return posts_show_list


@router.get('/read_all/categories',
            response_model=list[schemas.Category],
            status_code=status.HTTP_200_OK,
            summary='Get All Posts Categories')
@cache(expire=300, namespace=models.Category.__tablename__)
async def read_post_categories(db: DatabaseDependency,
                               skip: int = 0,
                               limit: int = 100) -> list[Type[models.Category]]:
    """
    Obtain all categories with `skip` and `limit`.
    """
    return await CrudManager(db, models.Category).retrieve(many=True, skip=skip, limit=limit)


@router.put('/update/{post_id}',
            response_model=schemas.PostShow,
            status_code=status.HTTP_200_OK,
            summary='Update Post By Passed `post_id`',
            dependencies=[CsrfVerifyDependency])
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/update/{post_id}')
async def update_post(post_id: int,
                      data: schemas.PostUpdate,
                      current_user: SecurityScopesDependency(scopes=['post:update']),
                      db: DatabaseDependency) -> Union[schemas.PostShow, HTTPException]:
    """
    Update post's data.
    """
    query = await crud.get_post_by_id_query(post_id)
    db_post = db.execute(query).scalar()
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
    updated_post_query = await crud.update_post_query(db, db_post, post_data_dict)
    post = db.execute(updated_post_query).mappings().first()
    post_show = create_post_show_instance_with_extra_attributes(post)
    return post_show


@router.delete('/delete/{post_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               summary='Delete Post By Passed `post_id`',
               dependencies=[CsrfVerifyDependency])
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/delete/{post_id}')
async def delete_post(db: DatabaseDependency,
                      current_user: SecurityScopesDependency(scopes=['post:delete']),
                      post_id: int) -> None:
    """
    Remove post by its `post_id`
    """
    query = await crud.get_post_by_id_query(post_id)
    db_post = db.execute(query).scalar()
    if not db_post:
        raise show_exception('post', status.HTTP_404_NOT_FOUND)
    # post can be deleted only by its owner or staff users
    if not is_object_owner_or_staff_user(db_post, current_user):
        raise show_exception('post', status.HTTP_403_FORBIDDEN)

    await CrudManager(db, models.Post).destroy(db_post)


@router.post('/create_comment/{post_id}',
             response_model=schemas.CommentShow,
             status_code=status.HTTP_201_CREATED,
             summary='Create Comment For Post With `post_id`',
             dependencies=[CsrfVerifyDependency])
async def create_comment(db: DatabaseDependency,
                         current_user: SecurityScopesDependency(scopes=['comment:create']),
                         comment: schemas.CommentCreateOrUpdate,
                         post_id: int) -> models.Comment:
    """
    Create comment for post with id `post_id` behalf `current_user`.
    """
    query = await crud.get_post_by_id_query(post_id)
    db_post = db.execute(query).first()
    if not db_post:
        raise show_exception('post', status.HTTP_404_NOT_FOUND)
    return await CrudManager(db, models.Comment).create({
        'body': comment.body,
        'post_id': post_id,
        'owner_id': current_user.id
    })


@router.post('/comment/{action}/{comment_id}',
             response_model=schemas.CommentShow,
             status_code=status.HTTP_200_OK,
             summary='Set Like Or Dislike `action` For Comment With `comment_id` Behalf Current User',
             dependencies=[CsrfVerifyDependency])
async def set_comment_like_or_dislike(db: DatabaseDependency,
                                      current_user: SecurityScopesDependency(scopes=['comment:rate']),
                                      comment_id: int,
                                      action: str) -> models.Comment:
    """
    Set like/dislike for comment with `comment_id` behalf `current_user`.
    """
    current_user = db.merge(current_user)  # copy instance into current session `db`
    db_comment = await CrudManager(db, models.Comment).retrieve(models.Comment.id == comment_id)
    if not db_comment:
        raise show_exception('comment', status.HTTP_404_NOT_FOUND)

    if action not in ('like', 'dislike'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Action is either like or dislike. Action <{action}> was passed'
        )

    return await crud.set_like_or_dislike_for_comment(db, current_user, db_comment, action)


@router.put('/comment/update/{comment_id}',
            response_model=schemas.CommentShow,
            status_code=status.HTTP_200_OK,
            summary='Update Comment By `comment_id`',
            dependencies=[CsrfVerifyDependency])
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/comment/update/{comment_id}')
async def update_comment(db: DatabaseDependency,
                         current_user: SecurityScopesDependency(scopes=['comment:update']),
                         data: schemas.CommentCreateOrUpdate,
                         comment_id: int) -> models.Comment:
    """
    Update comment by `comment_id`.
    """
    crud_manager = CrudManager(db, models.Comment)
    db_comment = await crud_manager.retrieve(models.Comment.id == comment_id)
    if not db_comment:
        raise show_exception('comment', status.HTTP_404_NOT_FOUND)
    # comment can be updated only by its owner or staff users
    if not is_object_owner_or_staff_user(db_comment, current_user):
        raise show_exception('comment', status.HTTP_403_FORBIDDEN)

    data_to_update = data.model_dump(exclude_none=True)
    return await crud_manager.update(db_comment, data_to_update)


@router.delete('/comment/delete/{comment_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               summary='Delete Comment By `comment_id`',
               dependencies=[CsrfVerifyDependency])
async def remove_comment(db: DatabaseDependency,
                         current_user: SecurityScopesDependency(scopes=['comment:delete']),
                         comment_id: int) -> None:
    """
    Delete comment by passed `comment_id`.
    """
    crud_manager = CrudManager(db, models.Comment)
    db_comment = await crud_manager.retrieve(models.Comment.id == comment_id)
    if db_comment is None:
        raise show_exception('comment', status.HTTP_404_NOT_FOUND)
    if not is_object_owner_or_staff_user(db_comment, current_user):
        raise show_exception('comment', status.HTTP_403_FORBIDDEN)
    await crud_manager.destroy(db_comment)
