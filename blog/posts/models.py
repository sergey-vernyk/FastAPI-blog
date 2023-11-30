from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, SmallInteger, Text, DateTime
from sqlalchemy.orm import relationship

from db_connection import Base


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
    created = Column('created', DateTime, default=datetime.utcnow)
    updated = Column('updated', DateTime, default=datetime.utcnow, onupdate=datetime.now)

    def __repr__(self):
        return f'`{self.tag}`:`{self.title[:50]}`, owner:`{self.owner}`'


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
