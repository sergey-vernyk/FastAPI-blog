from datetime import date

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """
    Common attributes while creating or reading data.
    """
    username: str = Field(max_length=30)
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    email: str = Field()


class UserCreate(UserBase):
    """
    Additional data (attributes) needed for creation user.
    """
    username: str
    first_name: str
    last_name: str | None
    password: str = Field(min_length=10)
    email: str
    date_of_birth: date
    role: str = Field(default='regular-user')


class User(UserBase):
    """
    Information which displays while obtaining user.
    """
    id: int
    username: str
    first_name: str
    last_name: str | None
    email: str
    role: str
    is_active: bool = Field(default=True)

    class Config:
        """
        Tell the Pydantic model to read the data even if it is not a dict,
        but an ORM model (or any other arbitrary object with attributes).
        """
        from_attributes = True


class UserUpdate(UserBase):
    """
    Info for update.
    """
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    hashed_password: str | None = None
    date_of_birth: date | None = None


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
