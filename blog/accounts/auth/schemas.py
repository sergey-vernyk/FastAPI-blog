from pydantic import BaseModel


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
