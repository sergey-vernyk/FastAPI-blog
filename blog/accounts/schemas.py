from datetime import date

from pydantic import BaseModel


class UserBase(BaseModel):
    """
    Common attributes while creating or reading data.
    """
    username: str
    first_name: str
    last_name: str
    email: str


class UserCreate(UserBase):
    """
    Additional data (attributes) needed for creation user.
    """
    username: str
    first_name: str
    last_name: str
    password: str
    email: str
    date_of_birth: date
    role: str = 'regular-user'


class User(UserBase):
    """
    Information which displays while obtaining user.
    """
    id: int
    username: str
    first_name: str
    last_name: str
    role: str
    is_active: bool

    class Config:
        """
        Tell the Pydantic model to read the data even if it is not a dict,
        but an ORM model (or any other arbitrary object with attributes).
        """
        from_attributes = True
