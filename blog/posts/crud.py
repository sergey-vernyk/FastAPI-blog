from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from accounts import schemas as user_schemas
from . import models, schemas
from .models import Post, Category


def get_post_by_title(db: Session, post_title: str) -> Post | None:
    """
    Get post by its `post_title`.
    """
    return db.query(models.Post).filter(models.Post.title == post_title).first()


def get_post_by_id(db: Session, post_id: int) -> Post | None:
    """
    Get post by its `post_id`.
    """
    return db.query(models.Post).get(ident=post_id)


def get_category_by_name(db: Session, name: str) -> Category | None:
    """
    Get category by its name.
    """
    return db.query(models.Category).filter(models.Category.name == name).first()


def create_post(db: Session,
                post: schemas.PostCreate,
                user: user_schemas.UserShow) -> Post:
    """
    Create post by passed parameters.
    """
    category = get_category_by_name(db, post.category)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Passed category does not exists'
        )
    post = models.Post(title=post.title,
                       body=post.body,
                       tags=','.join(post.tags),
                       category_id=category.id,
                       owner_id=user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def create_category(db: Session,
                    category: schemas.CategoryCreate,
                    user: user_schemas.UserCreate) -> Category:
    """
    Create post's category by passed parameters.
    """
    if user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only admin users be able to perform this action'
        )

    category = models.Category(name=category.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_post(db: Session,
                post: Post,
                user: user_schemas.UserUpdate,
                data_to_update: dict) -> Post:
    """
    Update post with passed parameters.
    """
    db.query(models.Post).filter(models.Post.id == post.id).update(data_to_update)
    db.commit()
    db.refresh(post)
    return post
