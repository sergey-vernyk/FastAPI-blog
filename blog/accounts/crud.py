from typing import Type

from sqlalchemy.orm import Session

from . import models, schemas, security
from .models import User


def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Obtain user by its `email` address.
    """
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[Type[User]]:
    """
    Obtain users from db with `limit` and offset `skip`.
    """
    return db.query(models.User).offset(skip).limit(limit).all()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """
    Obtain user by its `user_id`
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """
    Obtain user by its `username`.
    """
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate) -> User:
    """
    Create user by passed parameters.
    """
    hashed_password = security.get_password_hash(user.password)
    # Create a SQLAlchemy model instance with your data
    user = models.User(email=user.email,
                       hashed_password=hashed_password,
                       first_name=user.first_name,
                       last_name=user.last_name,
                       username=user.username,
                       role=user.role,
                       date_of_birth=user.date_of_birth)
    db.add(user)  # `add` that instance object to database session
    db.commit()  # save changes to the database
    db.refresh(user)  # refresh instance
    return user


def update_user(db: Session, user: User, data_to_update: dict) -> User:
    """
    Update user info from `data_to_update`.
    """
    # if user decided to change password, it has to text password as plain text
    # and passed password will convert to hash value
    if 'hashed_password' in data_to_update:
        data_to_update['hashed_password'] = security.get_password_hash(data_to_update['hashed_password'])

    db.query(models.User).filter(models.User.username == user.username).update(data_to_update)
    db.commit()
    db.refresh(user)
    return user
