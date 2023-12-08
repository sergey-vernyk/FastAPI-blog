from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from accounts.schemas import UsersLikesDislikesShow


class CategoryCreate(BaseModel):
    """
    Information which displays while creating post category.
    """
    name: str


class PostShowBriefly(BaseModel):
    """
    Briefly info about post.
    """
    id: int
    title: str
    tags: str


class Category(BaseModel):
    """
    Information about post category.
    """
    id: int
    name: str
    posts: List[PostShowBriefly]


class PostCreate(BaseModel):
    """
    Information needed for creating post.
    """
    title: str = Field(max_length=512)
    body: str = Field(max_length=2000)
    tags: List[str]
    category: str = Field(max_length=50)


class PostUpdate(PostCreate):
    """
    Information for update post.
    """
    is_publish: bool = Field(default=False)
    rating: int = Field(ge=0, le=5)


class UserPostsShow(BaseModel):
    """
    Posts which had been written behalf user.
    """
    id: int
    title: str
    tags: str
    category: CategoryCreate
    rating: int = Field(ge=0, le=5, default=0)
    is_publish: bool
    created: datetime
    updated: datetime


class CommentCreateOrUpdate(BaseModel):
    """
    Info for creating comment about a post.
    """
    body: str = Field(max_length=600)


class CommentShow(CommentCreateOrUpdate):
    """
    Info for display comment info.
    """
    id: int
    likes: list[UsersLikesDislikesShow]
    dislikes: list[UsersLikesDislikesShow]


class PostShow(BaseModel):
    """
    Information which displays while obtaining post.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count_comments = kwargs['count_comments']

    id: int
    title: str
    tags: str
    body: str = Field(max_length=2000)
    category: CategoryCreate
    rating: int = Field(ge=0, le=5, default=0)
    updated: datetime
    created: datetime
    count_comments: int
    comments: list[CommentShow]

    class Config:
        from_attributes = True


class UserCommentsShow(BaseModel):
    """
    Info for displaying comments that related to particular user.
    """
    post: PostShowBriefly
    body: str
    likes: list[UsersLikesDislikesShow]
    dislikes: list[UsersLikesDislikesShow]
