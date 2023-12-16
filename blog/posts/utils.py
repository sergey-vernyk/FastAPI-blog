from fastapi.encoders import jsonable_encoder
from sqlalchemy import RowMapping

from accounts.schemas import UserShowBriefly
from posts.schemas import CategoryCreate, CommentShow, PostShow


def create_post_show_instance_with_extra_attributes(post_row: RowMapping) -> PostShow:
    """
    Returns a `PostShow` instance with post category name, comments,
    comments likes/dislikes, post's owner and count of comments for a post.
    """
    post = dict(post_row)['Post']
    category = CategoryCreate(name=post.category.name)
    owner = UserShowBriefly(id=post.owner_id, username=post.owner.username)
    comments = [CommentShow(id=comment.id, body=comment.body,
                            likes=[
                                UserShowBriefly(id=like.id, username=like.username)
                                for like in comment.likes],
                            dislikes=[
                                UserShowBriefly(id=dislike.id, username=dislike.username)
                                for dislike in comment.dislikes])
                for comment in post.comments]

    data_for_post_show = {
        'comments': comments,
        'count_comments': post_row['count_comments'],
        'category': category,
        'owner': owner
    }
    data_for_post_show.update(**jsonable_encoder(post))
    return PostShow(**data_for_post_show)
