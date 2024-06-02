from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime,
    ForeignKey, Integer, SmallInteger,
    String, Table, Text
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from db_connection import Base


class ItemModel(Base):
    """
    Common model for entity in database.
    """

    __abstract__ = True

    created = Column('created', DateTime, default=datetime.now)
    updated = Column('updated', DateTime, default=datetime.now, onupdate=datetime.now)


# association tables for likes and dislikes for user
likes_table = Table(
    'likes',
    Base.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('comment_id', ForeignKey('comments.id', ondelete='CASCADE'), nullable=False),
    Column('user_id', ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
)

dislikes_table = Table(
    'dislikes',
    Base.metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('comment_id', ForeignKey('comments.id', ondelete='CASCADE'), nullable=False),
    Column('user_id', ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
)


class Post(ItemModel):
    """
    Information about post, that user will be able to write.
    """

    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, index=True)
    title = Column('title', String(512), nullable=False, unique=True)
    body = Column('body', Text, nullable=False)
    tags = Column('tags', ARRAY(String(30)), nullable=False)
    category = relationship('Category', back_populates='posts', lazy='selectin')
    category_id = Column(Integer, ForeignKey('postcategories.id', ondelete='CASCADE'))
    owner = relationship('User', back_populates='posts', lazy='selectin')
    owner_id = Column(Integer, ForeignKey('users.id'))
    rating = Column('rating', SmallInteger, default=0)
    is_publish = Column('is_publish', Boolean, default=False)
    comments = relationship('Comment', back_populates='post', passive_deletes=True, lazy='selectin')

    def __repr__(self):
        return f'Post:`{self.title[:50]}`, owner:`{self.owner}`'


class Category(Base):
    """
    Post's category.
    """

    __tablename__ = 'postcategories'

    id = Column(Integer, primary_key=True, index=True)
    name = Column('name', String(50), unique=True)
    posts = relationship('Post', back_populates='category', passive_deletes=True, lazy='selectin')

    def __repr__(self):
        return f'Post category: `{self.name}`'


class Comment(ItemModel):
    """
    Post's comment.
    """

    __tablename__ = 'comments'

    id = Column('id', Integer, primary_key=True, index=True)
    body = Column('body', String(600), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'))
    owner_id = Column(Integer, ForeignKey('users.id'))
    owner = relationship('User', back_populates='comments', lazy='selectin')
    likes = relationship('User', secondary=likes_table, passive_deletes=True, lazy='selectin')
    dislikes = relationship('User', secondary=dislikes_table, passive_deletes=True, lazy='selectin')
    post = relationship('Post', back_populates='comments', lazy='selectin')

    def __repr__(self):
        return f'Comment `{self.body[:70]}`'
