from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """
    Data (attributes) needed for creation user.
    """
    username: str = Field(max_length=30)
    first_name: str = Field(max_length=50)
    last_name: Optional[str] = Field(max_length=50, default=None)
    email: str
    password: str = Field(min_length=10)
    date_of_birth: Optional[date] = None
    role: str = Field(default='regular-user')


class UserShow(BaseModel):
    """
    Information which displays while obtaining user.
    """
    id: int
    username: str = Field(max_length=30)
    first_name: str = Field(max_length=50)
    last_name: Optional[str]
    email: str = Field()
    role: str
    is_active: bool

    class Config:
        """
        Tell the Pydantic model to read the data even if it is not a dict,
        but an ORM model (or any other arbitrary object with attributes).
        """
        from_attributes = True


class UserUpdate(BaseModel):
    """
    Info for update.
    """
    username: Optional[str] = Field(max_length=30, default=None)
    first_name: Optional[str] = Field(max_length=50, default=None)
    last_name: Optional[str] = Field(max_length=50, default=None)
    email: Optional[str] = Field(default='example@example.com')
    hashed_password: Optional[str] = Field(min_length=10, default=None)
    date_of_birth: Optional[date] = Field(default='yyy-mm-dd')
    is_active: Optional[bool] = Field(default=True)


class ResetUserPassword(BaseModel):
    """
    Info for reset forgotten user's password.
    """
    email: Optional[str] = None
    username: Optional[str] = None
    password: str = Field(min_length=10)


class Token(BaseModel):
    """
    Define data types for token.
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Data for get user from passed token.
    """
    username: str | None = None
