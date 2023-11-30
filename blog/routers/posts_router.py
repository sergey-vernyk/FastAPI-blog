from typing import Annotated

from fastapi import APIRouter, status, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from accounts.models import User
from dependencies import get_current_user, get_db
from posts import schemas, models, crud

router = APIRouter()


@router.post('/posts/create',
             response_model=schemas.PostShow,
             status_code=status.HTTP_201_CREATED,
             summary='Create post')
async def create_post(current_user: Annotated[User, Depends(get_current_user)],
                      post: schemas.PostCreate,
                      db: Session = Depends(get_db)) -> models.Post:
    """
    Create `post` behalf `current_user`.
    """
    # check if post with passed title not exists
    db_post = crud.get_post_by_title(db, post_title=post.title)
    if db_post:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Post already exists'
        )
    return crud.create_post(db, post, current_user)


@router.post('/post-category/create',
             response_model=schemas.CategoryCreate,
             status_code=status.HTTP_201_CREATED,
             summary='Create post category')
async def create_category(current_user: Annotated[User, Depends(get_current_user)],
                          category: schemas.CategoryCreate,
                          db: Session = Depends(get_db)) -> models.Category:
    """
    Create post's `category`.
    """
    db_category = crud.get_category_by_name(db, category.name)
    if db_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Category already exists'
        )
    return crud.create_category(db, category, current_user)


@router.put('/posts/update/{post_id}',
            response_model=schemas.PostUpdate,
            status_code=status.HTTP_200_OK,
            summary='Update post by `post_id`')
def update_post(post_id: int,
                data: schemas.PostUpdate,
                current_user: Annotated[User, Depends(get_current_user)],
                db: Session = Depends(get_db)) -> models.Post:
    """
    Update post data.
    """
    db_post = crud.get_post_by_id(db, post_id)
    if not db_post:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail='Post with passed id does not exists'
        )
    # current_post_data = jsonable_encoder(db_post)
    data_to_update = data.model_dump(exclude={'id'})
    post_data_dict = jsonable_encoder(data_to_update)
    return crud.update_post(db, db_post, current_user, post_data_dict)
