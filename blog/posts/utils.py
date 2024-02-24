from typing import TypeVar, Union

from fastapi.encoders import jsonable_encoder
from sqlalchemy import RowMapping

from accounts.models import User
from accounts.schemas import UserShowBriefly
from posts.models import Post
from posts.schemas import CategoryCreate, CommentShow, PostShow

PostInstance = TypeVar('PostInstance', bound=Post)


def create_post_show_instance_with_extra_attributes(post_row: Union[RowMapping, PostInstance]) -> PostShow:
    """
    Returns a `PostShow` instance with post category name, comments,
    comments likes/dislikes, post's owner and count of comments for a post.
    """
    post = None
    if isinstance(post_row, RowMapping):
        post = dict(post_row)['Post']
    elif isinstance(post_row, Post):
        post = post_row

    category = CategoryCreate(name=post.category.name)
    owner = UserShowBriefly(id=post.owner_id, username=post.owner.username)
    comments = [CommentShow(id=comment.id, body=comment.body,
                            created=comment.created, updated=comment.updated,
                            likes=[
                                UserShowBriefly(id=like.id, username=like.username)
                                for like in comment.likes
                            ],
                            dislikes=[
                                UserShowBriefly(id=dislike.id, username=dislike.username)
                                for dislike in comment.dislikes
                            ])
                for comment in post.comments]
    # exclude all data from `post` relationships to avoid recursion exceeded limit
    data_for_post_show = jsonable_encoder(post, exclude={'category', 'owner', 'comments'})
    data_for_post_show.update({
        'comments': comments,
        'count_comments': post_row['count_comments'] if isinstance(post_row, RowMapping) else len(post.comments),
        'category': category,
        'owner': owner,
        'tags': post.tags
    })
    return PostShow(**data_for_post_show)


def is_object_owner_or_staff_user(obj, user: User) -> bool:
    """
    Returns `True` if `user` is `obj`'s owner or `user` is staff user,
    or returns `False` otherwise.
    """
    return user.id == obj.owner_id or user.role in ('admin', 'moderator')
