from sqlalchemy import Boolean, Column, Integer, String, Date
from sqlalchemy import types
from sqlalchemy.orm import relationship

from db_connection import Base


class ChoiceType(types.TypeDecorator):
    """
    Class allows use choices in model's field.
    """
    impl = types.String

    def __init__(self, choices, **kwargs):
        self.choices = dict(choices)
        super().__init__(**kwargs)

    def process_bind_param(self, value, dialect):
        return [k for k in self.choices.keys() if k == value][0]

    def process_result_value(self, value, dialect):
        return self.choices[value]


class User(Base):
    """
    Information about user.
    """

    __tablename__ = 'users'  # table's name in database

    id = Column(Integer, primary_key=True, index=True)
    username = Column('username', String(30), nullable=False, unique=True)
    role = Column('role', ChoiceType(
        {
            'admin': 'admin',
            'regular-user': 'regular user',
            'moderator': 'moderator'
        }
    ), default='regular-user', nullable=False)
    first_name = Column('first_name', String(50))
    last_name = Column('last_name', String(50))
    date_of_birth = Column('date_of_birth', Date())
    email = Column('email', String, unique=True, index=True, nullable=False)
    hashed_password = Column(String)
    is_active = Column('is_active', Boolean, default=True)
    posts = relationship('Post', back_populates='owner')

    def __repr__(self):
        return f'User `{self.username}`'
