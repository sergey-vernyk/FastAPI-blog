from typing import Union

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from posts.models import Post, Category, Comment
from .models import User


async def get_current_user_posts(db: AsyncSession, user: User, criteria: Union[dict, None]) -> list[Post]:
    """
    Retrieve all posts in which `user` is as owner.
    Result can be different depends on `criteria` data, if any.
    """

    if criteria is None:
        statement = (
            select(Post)
            .join(Category)
            .filter(Post.owner.has(User.id == user.id))
        )
    else:
        statement = (
            select(Post)
            .join(Category)
            .filter(Post.owner.has(User.id == user.id),
                    or_(*[Post.tags.contains([tag]) for tag in criteria['tags']]),
                    Category.name.icontains(criteria['category']),
                    Post.rating.op('>=')(criteria['rating']),
                    Post.is_publish.is_(criteria['is_publish'])).distinct())
    buffered_posts = await db.execute(statement)
    posts = buffered_posts.scalars().all()
    return list(posts)


async def get_comments_for_user(db: AsyncSession,
                                user: User,
                                status: str,
                                skip: int = 0,
                                limit: int = 100) -> list[Comment]:
    """
    Obtain comments whom owner is `user`.
    The choice is obtained all user's comment or either only liked comment or disliked.
    """
    statement = (
        select(Comment)
        .join(User)
        .where(Comment.owner.has(User.id == user.id))
        .order_by('created')
    )

    if status == 'like':
        statement = statement.where(Comment.likes)  # get comments which got like
    elif status == 'dislike':
        statement = statement.where(Comment.dislikes)  # get comments which got dislike

    # get all comments
    statement = statement.offset(skip).limit(limit)
    buffered_comments = await db.execute(statement)
    comments_row_mapping = (comment._mapping for comment in buffered_comments.all())
    return [comment['Comment'] for comment in comments_row_mapping]
