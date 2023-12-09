from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime,
    ForeignKey, Integer, SmallInteger,
    String, Table, Text
)
from sqlalchemy.orm import relationship

from db_connection import Base

# association tables for likes and dislikes for user
likes_table = Table(
    'likes',
    Base.metadata,
    Column('id', primary_key=True, index=True),
    Column('comment_id', ForeignKey('comments.id'), nullable=False),
    Column('user_id', ForeignKey('users.id'), nullable=False),
)

dislikes_table = Table(
    'dislikes',
    Base.metadata,
    Column('id', primary_key=True, index=True),
    Column('comment_id', ForeignKey('comments.id'), nullable=False),
    Column('user_id', ForeignKey('users.id'), nullable=False),
)


class Post(Base):
    """
    Information about post, that user will be able to write.
    """

    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, index=True)
    title = Column('title', String(512), nullable=False, unique=True)
    body = Column('body', Text(2000), nullable=False)
    tags = Column('tags', String(100), nullable=False)
    category = relationship('Category', back_populates='posts')
    category_id = Column(Integer, ForeignKey('postcategories.id'))
    owner = relationship('User', back_populates='posts')
    owner_id = Column(Integer, ForeignKey('users.id'))
    rating = Column('rating', SmallInteger, default=0)
    is_publish = Column('is_publish', Boolean, default=False)
    comments = relationship('Comment', back_populates='post')
    created = Column('created', DateTime, default=datetime.utcnow)
    updated = Column('updated', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'Post:`{self.title[:50]}`, owner:`{self.owner}`'


class Category(Base):
    """
    Post's category.
    """

    __tablename__ = 'postcategories'

    id = Column(Integer, primary_key=True, index=True)
    name = Column('name', String(50), unique=True)
    posts = relationship('Post', back_populates='category')

    def __repr__(self):
        return f'Post category: `{self.name}`'


class Comment(Base):
    """
    Post's comment.
    """

    __tablename__ = 'comments'

    id = Column('id', Integer, primary_key=True, index=True)
    body = Column('body', String(600), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'))
    owner_id = Column(Integer, ForeignKey('users.id'))
    owner = relationship('User', back_populates='comments')
    likes = relationship('User', secondary=likes_table)
    dislikes = relationship('User', secondary=dislikes_table)
    post = relationship('Post', back_populates='comments')

    def __repr__(self):
        return f'Comment `{self.body[:70]}`'
