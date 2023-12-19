from typing import Type, Union

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from posts.models import Post, Category, Comment
from . import models, schemas, security
from .models import User


def get_user_by_email(db: Session, email: str) -> Union[User, None]:
    """
    Obtain user by its `email` address.
    """
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[Type[User]]:
    """
    Obtain users from db with `limit` and offset `skip`.
    """
    return db.query(models.User).order_by('id').offset(skip).limit(limit).all()


def get_user_by_id(db: Session, user_id: int) -> Union[User, None]:
    """
    Obtain user by its `user_id`
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Union[User, None]:
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
                       gender=user.gender,
                       username=user.username,
                       date_of_birth=user.date_of_birth)
    db.add(user)  # `add` that instance object to database session
    db.commit()  # save changes to the database
    db.refresh(user)  # refresh instance
    return user


def delete_user(db: Session, user: User) -> None:
    """
    Remove `user` from db.
    """
    db.delete(user)
    db.commit()


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


def get_current_user_posts(db: Session, user: User, criteria: Union[dict, None]) -> list[Post]:
    """
    Retrieve all posts in which `user` as owner.
    Result can be different depends on `criteria` data if any.
    """
    if criteria is None:
        statement = select(Post).join(Category).filter(Post.owner.has(User.id == user.id))
    else:
        statement = select(Post).join(Category).filter(
            Post.owner.has(User.id == user.id),
            Post.tags.icontains(','.join(criteria['tags'])),
            Category.name.icontains(criteria['category']),
            Post.rating.op('>=')(criteria['rating']),
            Post.is_publish.is_(criteria['is_publish'])).distinct()
    result = db.execute(statement)
    return list(result.scalars())


def get_comments_for_user(db: Session,
                          user: User,
                          status: str,
                          skip: int = 0,
                          limit: int = 100) -> list[Type[Comment]]:
    """
    Obtain comments whom owner is `user`.
    The choice is obtained all user's comment or either only liked comment or disliked.
    """
    comments = db.query(Comment).join(User).filter(Comment.owner.has(User.id == user.id)).order_by('created')

    if status == 'like':
        comments = comments.filter(Comment.likes)  # get comments which got like
    elif status == 'dislike':
        comments = comments.filter(Comment.dislikes)  # get comments which got dislike

    return comments.offset(skip).limit(limit).all()


def reset_user_password(db: Session, data: dict) -> None:
    """
    Reset user's account password.
    """
    user = None
    # select between email or username (depends upon what was passed)
    if data['email']:
        user = get_user_by_email(db, data.get('email'))
    elif data['username']:
        user = get_user_by_username(db, data.get('username'))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Username or email was not passed'
        )

    # hashing plain password
    hashed_password = security.get_password_hash(data['password'])
    db.query(User).filter(models.User.id == user.id).update({'hashed_password': hashed_password})
    db.commit()
