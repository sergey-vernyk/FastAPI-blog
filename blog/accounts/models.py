from sqlalchemy import Boolean, Column, Integer, String, Date, Text
from sqlalchemy import types
from sqlalchemy.orm import relationship

from db_connection import Base
from posts.models import likes_table, dislikes_table


class ChoiceType(types.TypeDecorator):
    """
    Class allows use choices in model's field.
    """
    impl = types.String
    cache_ok = True

    def __init__(self, choices, **kwargs) -> None:
        self.choices = tuple(choices)
        super().__init__(**kwargs)

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        return value


class User(Base):
    """
    Information about user.
    """

    __tablename__ = 'users'  # table's name in database

    id = Column(Integer, primary_key=True, index=True)
    username = Column('username', String(30), nullable=False, unique=True)
    role = Column('role', ChoiceType(
        (
            'admin',
            'regular-user',
            'moderator'
        )
    ), default='regular-user', nullable=False)
    first_name = Column('first_name', String(50))
    last_name = Column('last_name', String(50))
    image = Column('image', String, nullable=True)
    gender = Column('gender', ChoiceType(
        (
            'male',
            'female'
        )
    ), nullable=True)
    date_of_birth = Column('date_of_birth', Date())
    email = Column('email', String, unique=True, index=True, nullable=False)
    hashed_password = Column(String)
    is_active = Column('is_active', Boolean, default=True)
    posts = relationship('Post', back_populates='owner')
    likes = relationship('Comment', secondary=likes_table, viewonly=True)
    dislikes = relationship('Comment', secondary=dislikes_table, viewonly=True)
    comments = relationship('Comment', back_populates='owner')
    about = Column('about', Text, nullable=True)

    def __repr__(self):
        return f'User `{self.username}`'
