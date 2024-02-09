from typing import Type, Union

from fastapi import HTTPException
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from accounts.models import User
from . import schemas
from .models import Category, Post, Comment


def get_post_by_title(db: Session, post_title: str) -> Union[Post, None]:
    """
    Get post by its `post_title`.
    """
    return db.query(Post).filter(Post.title == post_title).first()


def get_post_by_id_query(post_id: int) -> Select:
    """
    Get post by its `post_id`.
    """
    return select(Post, func.count(Comment.id).label('count_comments')).join(
        Category).outerjoin(Comment).filter(Post.id == post_id).group_by(Post.id)


def get_category_by_name(db: Session, name: str) -> Union[Category, None]:
    """
    Get category by its name.
    """
    return db.query(Category).filter(Category.name == name).first()


def create_post(db: Session, post: schemas.PostCreate, category_id: int, user: User) -> Union[HTTPException, Post]:
    """
    Create post by passed parameters.
    """
    post = Post(title=post.title,
                body=post.body,
                tags=','.join(post.tags),
                category_id=category_id,
                owner_id=user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def create_category(db: Session,
                    category: schemas.CategoryCreate) -> Category:
    """
    Create post's category by passed parameters.
    """
    category = Category(name=category.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def get_posts_query(category: str, skip: int = 0, limit: int = 100, sort_by: str = 'created_desc') -> Select:
    """
    Return query for get all posts in the `db` with offset `skip` and `limit`,
    and sort results by criteria from `sort_by`.
    """
    sort_conditions = {
        'created_asc': Post.created,
        'rating_asc': Post.rating,
        'post_comments_asc': func.count(Post.comments).label('post_comments'),
        'created_desc': desc(Post.created),
        'rating_desc': desc(Post.rating),
        'post_comments_desc': desc(func.count(Post.comments).label('post_comments'))
    }
    return select(Post, func.count(Comment.id).label('count_comments')).join(Category).outerjoin(
        Comment).filter(Category.name.icontains(category)).group_by(
        Post.id).order_by(sort_conditions[sort_by]).offset(skip).limit(limit)


def get_post_categories(db: Session, skip: int = 0, limit: int = 100) -> list[Type[Category]]:
    """
    Return all categories in the `db` with offset `skip` and `limit`.
    """
    return db.query(Category).offset(skip).limit(limit).all()


def update_post_query(db: Session, post: Post, data_to_update: dict) -> Select:
    """
    Update post with passed parameters and return query with the post along extra data.
    """
    db.query(Post).filter(Post.id == post.id).update(data_to_update)
    db.commit()
    return select(Post, func.count(Comment.id).label('count_comments')).join(
        Category).outerjoin(Comment).filter(Post.id == post.id).group_by(Post.id)


def delete_post(db: Session, post: Post) -> None:
    """
    Remove `post` from db.
    """
    db.delete(post)
    db.commit()


def create_comment(db: Session,
                   comment: schemas.CommentCreateOrUpdate,
                   user: schemas.UserShowBriefly,
                   post_id: int) -> Comment:
    """
    Create comment for `post_id` behalf `user`.
    """
    comment = Comment(
        body=comment.body,
        post_id=post_id,
        owner_id=user.id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comment_by_id(db: Session, comment_id: int) -> Union[Comment, None]:
    """
    Obtain comment with `comment_id` from db.
    """
    return db.get(Comment, comment_id)


def set_like_or_dislike_for_comment(db: Session, user: User, comment: Comment, action: str) -> Comment:
    """
    Set comment with `comment_id` as liked/disliked by `user`.
    """
    is_already_set_like = user in comment.likes
    is_already_set_dislike = user in comment.dislikes

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


def update_comment(db: Session, comment: Comment, data_to_update: dict) -> Comment:
    """
    Update comment's body.
    """
    db.query(Comment).filter(Comment.id == comment.id).update(data_to_update)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment: Comment) -> None:
    """
    Remove `comment` from database.
    """
    db.delete(comment)
    db.commit()
