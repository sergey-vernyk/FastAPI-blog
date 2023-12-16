from typing import Type, Union

from fastapi import HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from accounts import schemas as user_schemas
from accounts.models import User
from . import models, schemas
from .models import Category, Post


def get_post_by_title(db: Session, post_title: str) -> Union[Post, None]:
    """
    Get post by its `post_title`.
    """
    return db.query(models.Post).filter(models.Post.title == post_title).first()


def get_post_by_id(db: Session, post_id: int) -> Query:
    """
    Get post by its `post_id`.
    """
    return db.query(models.Post, func.count(models.Comment.id).label('count_comments')).join(
        models.Category).outerjoin(models.Comment).filter(models.Post.id == post_id).group_by(models.Post.id)


def get_category_by_name(db: Session, name: str) -> Union[Category, None]:
    """
    Get category by its name.
    """
    return db.query(models.Category).filter(models.Category.name == name).first()


def create_post(db: Session,
                post: schemas.PostCreate,
                user: user_schemas.UserShow) -> Union[HTTPException, Post]:
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
                    user: user_schemas.UserShow) -> Category:
    """
    Create post's category by passed parameters.
    """
    if user.role not in ('admin', 'moderator'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only admin users be able to perform this action'
        )

    category = models.Category(name=category.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def get_posts_query(db: Session, category: str, skip: int = 0, limit: int = 100) -> Query:
    """
    Return query for get all posts in the `db` with offset `skip` and `limit`.
    """
    return db.query(models.Post, func.count(models.Comment.id).label('count_comments')).join(
        models.Category).outerjoin(models.Comment).filter(models.Category.name.icontains(category)).group_by(
        models.Post.id).offset(skip).limit(limit)


def get_post_categories(db: Session, skip: int = 0, limit: int = 100) -> list[Type[Category]]:
    """
    Return all categories in the `db` with offset `skip` and `limit`.
    """
    return db.query(models.Category).offset(skip).limit(limit).all()


def update_post(db: Session, post: Post, data_to_update: dict) -> Query:
    """
    Update post with passed parameters.
    """
    db.query(models.Post).filter(models.Post.id == post.id).update(data_to_update)
    db.commit()
    query = db.query(models.Post, func.count(models.Comment.id).label('count_comments')).join(
        models.Category).outerjoin(models.Comment).filter(models.Post.id == post.id).group_by(models.Post.id)
    return query


def delete_post(db: Session, post: Post) -> None:
    """
    Remove `post` from db.
    """
    db.delete(post)
    db.commit()


def create_comment(db: Session,
                   comment: schemas.CommentCreateOrUpdate,
                   user: schemas.UserShowBriefly,
                   post_id: int) -> models.Comment:
    """
    Create comment for `post_id` behalf `user`.
    """
    comment = models.Comment(
        body=comment.body,
        post_id=post_id,
        owner_id=user.id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comment_by_id(db: Session, comment_id: int) -> Union[models.Comment, None]:
    """
    Obtain comment with `comment_id` from db.
    """
    return db.query(models.Comment).get(comment_id)


def set_like_or_dislike_for_comment(db: Session, user: User, comment: models.Comment, action: str) -> models.Comment:
    """
    Set comment with `comment_id` as liked/disliked by `user`.
    """
    is_already_set_like = user in comment.likes
    is_already_set_dislike = user in comment.dislikes

    if action not in ('like', 'dislike'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Action is either like or dislike. Action <{action}> was passed'
        )

    if action == 'like':
        # toggle from dislike to like
        if is_already_set_dislike:
            comment.dislikes.remove(user)
            comment.likes.append(user)
        elif is_already_set_like:
            comment.likes.remove(user)  # unset `like`
        elif not is_already_set_like:
            comment.likes.append(user)  # set `like`
    elif action == 'dislike':
        # toggle from like to dislike
        if is_already_set_like:
            comment.likes.remove(user)
            comment.dislikes.append(user)
        elif is_already_set_dislike:
            comment.dislikes.remove(user)  # unset `dislike`
        elif not is_already_set_dislike:
            comment.dislikes.append(user)  # set `dislike`

    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def update_comment(db: Session, comment: models.Comment, data_to_update: dict) -> models.Comment:
    """
    Update comment's body.
    """
    db.query(models.Comment).filter(models.Comment.id == comment.id).update(data_to_update)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment: models.Comment) -> None:
    """
    Remove `comment` from database.
    """
    db.delete(comment)
    db.commit()
