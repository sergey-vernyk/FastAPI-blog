from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, EmailStr


class UserCreate(BaseModel):
    """
    Data (attributes) needed for creation user.
    """
    username: str = Field(max_length=30)
    first_name: str = Field(max_length=50)
    last_name: Optional[str] = Field(max_length=50, default=None)
    gender: Optional[str] = Field(max_length=6, default=None, examples=['male/female'])
    email: EmailStr
    password: str = Field(min_length=10)
    date_of_birth: Optional[date] = None
    about: Optional[str] = Field(default=None, max_length=255)
    social_media_links: Optional[list[str]] = Field(default=[], max_length=2083)


class UserShow(BaseModel):
    """
    Information which displays while obtaining user.
    """

    id: int
    username: str
    first_name: str
    last_name: Optional[str]
    image: HttpUrl | None
    date_of_birth: date
    gender: str
    email: str
    role: str
    rating: int
    is_active: bool
    last_login: datetime | None
    date_joined: datetime | None
    about: str | None
    social_media_links: list[str] | None

    class Config:
        """
        Tell the Pydantic model to read the data even if it is not a dict,
        but an ORM model (or any other arbitrary object with attributes).
        """
        from_attributes = True


class UserUpdate(BaseModel):
    """
    Info for update user.
    """
    username: Optional[str] = Field(max_length=30, default=None)
    first_name: Optional[str] = Field(max_length=50, default=None)
    last_name: Optional[str] = Field(max_length=50, default=None)
    image: Optional[str] = None
    gender: Optional[str] = Field(max_length=6, default=None)
    email: Optional[EmailStr] = Field(examples=['example@example.com'], default=None)
    hashed_password: Optional[str] = Field(min_length=10, default=None)
    date_of_birth: Optional[date] = Field(examples=['yyyy-mm-dd'], default=None)
    is_active: Optional[bool] = Field(default=None)
    about: Optional[str] = Field(max_length=255, default=None)
    social_media_links: Optional[list[str]] = Field(default=[])


class UserShowBriefly(BaseModel):
    """
    Info about users, which are in likes and dislikes lists.
    """
    id: int
    username: str


class ResetUserPassword(BaseModel):
    """
    Info for reset forgotten user's password.
    """
    email: Optional[EmailStr] = None
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
    Data for get username and scopes from passed token.
    """
    username: str | None = None
    scopes: list[str] = []
