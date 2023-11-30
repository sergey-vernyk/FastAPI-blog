from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class Category(BaseModel):
    """
    Information about post category.
    """
    id: int
    name: str
    posts: list


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
    rating: int = Field(ge=0, lt=6, default=0)
    updated: datetime
    created: datetime

    class Config:
        from_attributes = True


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
    rating: int = Field(ge=0, lt=6)
