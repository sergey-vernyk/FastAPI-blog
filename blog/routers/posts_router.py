from typing import Type, Annotated, Union

from fastapi import APIRouter, status, HTTPException, Query, Security
from fastapi.encoders import jsonable_encoder

from accounts.models import User
from dependencies import (
    DatabaseDependency,
    get_current_user,
    SecurityScopesDependency
)
from posts import schemas, models, crud
from posts.utils import create_post_show_instance_with_extra_attributes

router = APIRouter()


def show_exception(sub: str, error: status) -> HTTPException:
    """
    Returns exception info about `sub` and explanation about `error` type.
    """
    info = {
        status.HTTP_404_NOT_FOUND: f'{sub.capitalize()} with passed id does not exists',
        status.HTTP_403_FORBIDDEN: f'{sub.capitalize()} can be updated only by staff users or by its owner',
        status.HTTP_400_BAD_REQUEST: f'{sub.capitalize()} already exists'
    }
    return HTTPException(status_code=error, detail=info[error])


@router.post('/create',
             response_model=schemas.PostShow,
             status_code=status.HTTP_201_CREATED,
             summary='Create post')
async def create_post(current_user: Annotated[User, Security(get_current_user, scopes=['post:create'])],
                      post: schemas.PostCreate,
                      db: DatabaseDependency) -> Union[schemas.PostShow, HTTPException]:
    """
    Create `post` behalf `current_user`.
    """
    # check if post with passed title not exists
    db_post = crud.get_post_by_title(db, post_title=post.title)
    if db_post:
        raise show_exception('post', status.HTTP_400_BAD_REQUEST)
    data_for_post_show = {}
    # get created post, encode it into JSON
    # instantiate other schemas which are in `PostShow` schema
    # fill data for `PostShow` instance and create it from that data
    post = crud.create_post(db, post, current_user)
    post_info = jsonable_encoder(post)
    category = schemas.CategoryCreate(name=post.category.name)
    data_for_post_show.update(comments=[], category=category, count_comments=0, **post_info)
    post_show = schemas.PostShow(**data_for_post_show)
    return post_show


@router.post('/category/create',
             response_model=schemas.CategoryCreate,
             status_code=status.HTTP_201_CREATED,
             summary='Create post category')
async def create_category(current_user: SecurityScopesDependency(['category:create']),
                          category: schemas.CategoryCreate,
                          db: DatabaseDependency) -> Union[models.Category, HTTPException]:
    """
    Create post's `category`.
    """
    db_category = crud.get_category_by_name(db, category.name)
    if db_category:
        raise show_exception('category', status.HTTP_400_BAD_REQUEST)
    return crud.create_category(db, category, current_user)


@router.get('/read/{post_id}',
            response_model=schemas.PostShow,
            status_code=status.HTTP_200_OK,
            summary='Get post by passed `post_id`')
async def read_post(db: DatabaseDependency,
                    post_id: int) -> schemas.PostShow:
    """
    Obtain post by its `post_id`.
    """
    query = crud.get_post_by_id(db, post_id)
    post = db.execute(query).mappings().first()
    if not post:
        raise show_exception('post', status.HTTP_404_NOT_FOUND)
    return create_post_show_instance_with_extra_attributes(post)


@router.get('/read_all/posts',
            response_model=list[schemas.PostShow],
            status_code=status.HTTP_200_OK,
            summary='Get all posts in the database')
async def read_posts(db: DatabaseDependency,
                     category: Annotated[str, Query(description='Post category')] = '',
                     skip: int = 0,
                     limit: int = 100) -> list[schemas.PostShow]:
    """
    Obtain all posts with `skip`, `limit` and appropriate `category` if it provided.
    """
    query = crud.get_posts_query(db, category, skip=skip, limit=limit)
    # rows with post's scalars values as list
    posts_rows = db.execute(query).mappings().all()
    posts_show_list = []  # result list for response
    for row in posts_rows:
        post_show = create_post_show_instance_with_extra_attributes(row)
        posts_show_list.append(post_show)

    return posts_show_list


@router.get('/read_all/categories',
            response_model=list[schemas.Category],
            status_code=status.HTTP_200_OK,
            summary='Get all post categories in the database')
async def read_post_categories(db: DatabaseDependency,
                               skip: int = 0,
                               limit: int = 100) -> list[Type[models.Category]]:
    """
    Obtain all categories with `skip` and `limit`.
    """
    return crud.get_post_categories(db, skip=skip, limit=limit)


@router.put('/update/{post_id}',
            response_model=schemas.PostShow,
            status_code=status.HTTP_200_OK,
            summary='Update post by passed `post_id`')
def update_post(post_id: int,
                data: schemas.PostUpdate,
                current_user: SecurityScopesDependency(scopes=['post:update']),
                db: DatabaseDependency) -> Union[schemas.PostShow, HTTPException]:
    """
    Update post's data.
    """
    db_post = crud.get_post_by_id(db, post_id)
    if not db_post:
        raise show_exception('post', status.HTTP_404_NOT_FOUND)
    # restriction update post only by staff users or post's owner,
    # even `current_user` has appropriate authorization scope
    if current_user.id != db_post.owner_id and current_user.role not in ('moderator', 'admin'):
        raise show_exception('post', status.HTTP_403_FORBIDDEN)
    data_to_update = data.model_dump(exclude={'id', 'category'})
    data_to_update.update({
        'category_id': db_post.category_id,
        'tags': ','.join(data_to_update['tags'])}
    )

    post_data_dict = jsonable_encoder(data_to_update)
    updated_post_query = crud.update_post(db, db_post, post_data_dict)
    post = db.execute(updated_post_query).mappings().first()
    post_show = create_post_show_instance_with_extra_attributes(post)
    return post_show


@router.delete('/delete/{post_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               summary='Delete post by passed `post_id`')
async def delete_post(db: DatabaseDependency,
                      current_user: SecurityScopesDependency(scopes=['post:delete']),
                      post_id: int) -> None:
    """
    Remove post by its `post_id`
    """
    db_post = crud.get_post_by_id(db, post_id)
    if not db_post:
        raise show_exception('post', status.HTTP_404_NOT_FOUND)
    if db_post.owner_id != post_id or current_user.role not in ('admin', 'moderator'):
        raise show_exception('post', status.HTTP_403_FORBIDDEN)
    crud.delete_post(db, db_post)


@router.post('/create_comment/{post_id}',
             response_model=schemas.CommentShow,
             status_code=status.HTTP_201_CREATED,
             summary='Create comment for post with `post_id`')
async def create_comment(db: DatabaseDependency,
                         current_user: SecurityScopesDependency(scopes=['comment:create']),
                         comment: schemas.CommentCreateOrUpdate,
                         post_id: int) -> models.Comment:
    """
    Create comment for post with id `post_id` behalf `current_user`.
    """
    db_post = crud.get_post_by_id(db, post_id)
    if not db_post:
        raise show_exception('post', status.HTTP_404_NOT_FOUND)
    return crud.create_comment(db, comment, current_user, post_id)


@router.post('/comment/{action}/{comment_id}',
             response_model=schemas.CommentShow,
             status_code=status.HTTP_200_OK,
             summary='Set like or dislike `action` for comment with `comment_id` behalf current user')
async def set_comment_like_or_dislike(db: DatabaseDependency,
                                      current_user: SecurityScopesDependency(scopes=['comment:rate']),
                                      comment_id: int,
                                      action: str) -> models.Comment:
    """
    Set like/dislike for comment with `comment_id` behalf `current_user`.
    """
    current_user = db.merge(current_user)  # copy instance into current session `db`
    db_comment = crud.get_comment_by_id(db, comment_id)
    if not db_comment:
        raise show_exception('comment', status.HTTP_404_NOT_FOUND)

    return crud.set_like_or_dislike_for_comment(db, current_user, db_comment, action)


@router.put('/comment/update/{comment_id}',
            response_model=schemas.CommentCreateOrUpdate,
            status_code=status.HTTP_200_OK,
            summary='Update comment with `comment_id`',
            dependencies=[Security(get_current_user, scopes=['comment:update'])])
async def update_comment(db: DatabaseDependency,
                         data: schemas.CommentCreateOrUpdate,
                         comment_id: int) -> models.Comment:
    """
    Update comment by `comment_id`.
    """
    db_comment = crud.get_comment_by_id(db, comment_id)
    if not db_comment:
        raise show_exception('comment', status.HTTP_404_NOT_FOUND)
    data_to_update = data.model_dump(exclude_none=True)
    return crud.update_comment(db, db_comment, data_to_update)


@router.delete('/comment/delete/{comment_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               summary='Delete comment with `comment_id`',
               dependencies=[Security(get_current_user, scopes=['comment:delete'])])
async def remove_comment(db: DatabaseDependency,
                         comment_id: int) -> None:
    """
    Delete comment by passed `comment_id`.
    """
    db_comment = crud.get_comment_by_id(db, comment_id)
    if not db_comment:
        raise show_exception('comment', status.HTTP_404_NOT_FOUND)
    crud.delete_comment(db, db_comment)
