from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from accounts.schemas import UserShowBriefly


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
    tags: List[str]

    model_config = ConfigDict(from_attributes=True)


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
    tags: List[str]
    category: CategoryCreate
    rating: int = Field(ge=0, le=5, default=0)
    is_publish: bool
    created: datetime
    updated: datetime

    model_config = ConfigDict(from_attributes=True)


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
    likes: list[UserShowBriefly]
    dislikes: list[UserShowBriefly]
    created: datetime
    updated: datetime

    model_config = ConfigDict(from_attributes=True)


class PostShow(BaseModel):
    """
    Information which displays while obtaining post.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.count_comments = kwargs.get('count_comments', 0)

    id: int
    title: str
    tags: List[str]
    body: str = Field(max_length=2000)
    category: CategoryCreate
    rating: int = Field(ge=0, le=5, default=0)
    updated: datetime
    created: datetime
    owner: UserShowBriefly
    is_publish: bool
    count_comments: int = 0
    comments: list[CommentShow] = []

    model_config = ConfigDict(from_attributes=True)


class UserCommentsShow(BaseModel):
    """
    Info for displaying comments that related to particular user.
    """

    id: int
    post: PostShowBriefly
    body: str
    likes: list[UserShowBriefly]
    dislikes: list[UserShowBriefly]
    created: datetime
    updated: datetime

    model_config = ConfigDict(from_attributes=True)
