from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from accounts.models import User
from common.tasks import invalidate_endpoint_cache
from .models import Category, Post, Comment


async def get_post_by_id_query(post_id: int) -> Select:
    """
    Get post by its `post_id`.
    """
    return (
        select(Post, func.count(Comment.id).label('count_comments'))
        .join(Category)
        .outerjoin(Comment)
        .filter(Post.id == post_id)
        .group_by(Post.id)
    )


async def get_posts_query(category: str,
                          skip: int = 0,
                          limit: int = 100,
                          sort_by: str = 'created_desc') -> Select:
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
    return (
        select(Post, func.count(Comment.id).label('count_comments'))
        .join(Category)
        .outerjoin(Comment)
        .filter(Category.name.icontains(category))
        .group_by(Post.id)
        .order_by(sort_conditions[sort_by])
        .offset(skip)
        .limit(limit)
    )


async def set_like_or_dislike_for_comment(db: AsyncSession, user: User, comment: Comment, action: str) -> Comment:
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
    await db.commit()
    await db.refresh(comment)
    # invalidate cache after comment's data has been updated
    invalidate_endpoint_cache.delay(namespace=Comment.__tablename__, request_method='get')
    return comment
