from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from blog.accounts.schemas import UsersLikesDislikesShow


class CategoryCreate(BaseModel):
    """
    Information which displays while creating post category.
    """
    name: str


class PostShow(BaseModel):
    """
    Information which displays while obtaining post.
    """
    id: int
    tags: str
    body: str = Field(max_length=2000)
    category: CategoryCreate
    rating: int = Field(ge=0, le=5, default=0)
    updated: datetime
    created: datetime

    class Config:
        from_attributes = True


class Category(BaseModel):
    """
    Information about post category.
    """
    id: int
    name: str
    posts: List[PostShow]


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
    Posts which has been written behalf user.
    """
    id: int
    title: str
    tags: str
    category: CategoryCreate
    rating: int = Field(ge=0, le=5, default=0)
    is_publish: bool
    created: datetime
    updated: datetime


class CommentCreate(BaseModel):
    """
    Info for creating comment about a post.
    """
    body: str = Field(max_length=600)


class CommentShow(CommentCreate):
    """
    Info for display comment info.
    """
    id: int
    post: PostShow
    likes: list[UsersLikesDislikesShow]
    dislikes: list[UsersLikesDislikesShow]
