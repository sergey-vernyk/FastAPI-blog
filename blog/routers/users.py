from typing import Type

from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.orm import Session

from accounts import schemas, models, crud
from dependencies import get_db

router = APIRouter()


@router.post('/users/', response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)) -> models.User:
    """
    Create user in database.
    """
    # try to get user by its email
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already registered')
    return crud.create_user(db=db, user=user)


@router.get('/users/', response_model=list[schemas.User], status_code=status.HTTP_200_OK)
def read_users(skip: int = 0,
               limit: int = 100,
               db: Session = Depends(get_db)) -> list[Type[models.User]]:
    """
    Obtain all users from database with `limit`.
    """
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@router.get('/users/{user_id}', response_model=schemas.User, status_code=status.HTTP_200_OK)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """
    Obtain user by its `user_id`.
    """
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail='User not found')
    return db_user
