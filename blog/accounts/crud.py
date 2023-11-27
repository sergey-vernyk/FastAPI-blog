from typing import Type, List

from sqlalchemy.orm import Session

from . import models, schemas


def get_user_by_email(db: Session, email: str) -> Type[models.User] | None:
    """
    Obtain user by its `email` address.
    """
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[Type[models.User]]:
    """
    Obtain users from db with `limit` and offset `skip`.
    """
    return db.query(models.User).offset(skip).limit(limit).all()


def get_user(db: Session, user_id: int):
    """
    Obtain user by its `user_id`
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """
    Create user by passed parameters.
    """
    fake_hashed_password = user.password + "notreallyhashed"
    # Create a SQLAlchemy model instance with your data
    db_user = models.User(email=user.email,
                          hashed_password=fake_hashed_password,
                          first_name=user.first_name,
                          last_name=user.last_name,
                          username=user.username,
                          role=user.role,
                          data_of_birth=user.date_of_birth)
    db.add(db_user)  # `add` that instance object to database session
    db.commit()  # save changes to the database
    db.refresh(db_user)  # refresh instance
    return db_user
