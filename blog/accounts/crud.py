from typing import Type, Union

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from posts.models import Post, Category, Comment
from .models import User


async def get_current_user_posts(db: Session, user: User, criteria: Union[dict, None]) -> list[Post]:
    """
    Retrieve all posts in which `user` as owner.
    Result can be different depends on `criteria` data if any.
    """

    if criteria is None:
        statement = select(Post).join(Category).filter(Post.owner.has(User.id == user.id))
    else:
        statement = select(Post).join(Category).filter(
            Post.owner.has(User.id == user.id),
            or_(*[Post.tags.contains([tag]) for tag in criteria['tags']]),
            Category.name.icontains(criteria['category']),
            Post.rating.op('>=')(criteria['rating']),
            Post.is_publish.is_(criteria['is_publish'])).distinct()
    result = db.execute(statement)
    return list(result.scalars())


async def get_comments_for_user(db: Session,
                                user: User,
                                status: str,
                                skip: int = 0,
                                limit: int = 100) -> list[Type[Comment]]:
    """
    Obtain comments whom owner is `user`.
    The choice is obtained all user's comment or either only liked comment or disliked.
    """
    comments = db.query(Comment).join(
        User).filter(Comment.owner.has(User.id == user.id)).order_by('created')

    if status == 'like':
        comments = comments.filter(Comment.likes)  # get comments which got like
    elif status == 'dislike':
        comments = comments.filter(Comment.dislikes)  # get comments which got dislike

    return comments.offset(skip).limit(limit).all()
