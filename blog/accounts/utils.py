import hashlib
import hmac
import os
from base64 import urlsafe_b64decode
from datetime import datetime
from secrets import compare_digest
from typing import Type, Union

from pathlib import Path
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from accounts import schemas, crud
from accounts.models import User
from common.utils import base36decode, base36encode
from config import get_settings


settings = get_settings()

# define parent directory path for the directory `static` (for possibility using relative path)
PARENT_DIR_PATH = str(Path(__file__).resolve().parent.parent)

USER_IMAGES_DIR_PATH = ''
if settings.dev_or_prod == 'dev':
    USER_IMAGES_DIR_PATH = f'{PARENT_DIR_PATH}/static/img/users_images/'
elif settings.dev_or_prod == 'prod':
    USER_IMAGES_DIR_PATH = '/vol/static/img/users_images/'


async def create_user_image_url(current_user: Union[User, Type[User]], scheme: str, domain: str) -> schemas.UserShow:
    """
    Create and return pydantic user model `UserShow` with updated attribute `image`
    by adding to the image's url (got from db) HTTP scheme and domain,
    e.g. `http://example.com/static/img/users_images/user/user_avatar.jpg`
    instead of `/static/img/users_images/user/user_avatar.jpg`.
    """

    user_image_url = f'{scheme}://{domain}/{current_user.image}' if current_user.image else None
    user_dict = jsonable_encoder(current_user, exclude={'image'})
    user_dict.update(image=user_image_url)
    user_show = schemas.UserShow(**user_dict)
    return user_show


def create_or_update_user_folder(current_user: User) -> None:
    """
    Create user folder for user's image or remove exists image before user uploaded new image.
    """
    # if user's folder does not exists
    if not os.path.isdir(f'{USER_IMAGES_DIR_PATH}{current_user.username}'):
        os.mkdir(f'{USER_IMAGES_DIR_PATH}{current_user.username}')
    # if there is an image inside user's folder
    if os.listdir(f'{USER_IMAGES_DIR_PATH}{current_user.username}'):
        os.system(f'rm {USER_IMAGES_DIR_PATH}{current_user.username}/*')


def verify_uid_and_token_from_url(db: Session, uidb64: str, token: str) -> Union[User, None]:
    """
    Verify `uidb64` string and token which obtained from url.
    Uidb64 is encoded string with username, token also is string generated from token generator,
    which taking in account user's data. The function check if `token` is still valid
    (not expired) and whether username from decoded `uidb64` is existing in database.
    If it is than will return user from database by its username.
    """
    try:
        # decoding user id from uidb64 and getting user from db
        username = urlsafe_b64decode(uidb64).decode('utf-8')
        user = crud.get_user_by_username(db, username)
    except (TypeError, ValueError):
        user = None
    # if user is exists and token term isn't end (token is valid)
    if user is not None and token_generator.check_token(user, token):
        return user
    return None


class LimitedLifeTokenGenerator:
    """
    Class used to generate and check tokens for the password
    reset or activate account mechanism.
    """

    key_salt = 'blog.account.utils.LimitedLifeTokenGenerator'
    algorithm = None

    def __init__(self, secret_key: str, token_expired_timeout: int) -> None:
        assert settings.token_expired_timeout, '`TOKEN_EXPIRED_TIMEOUT` must be provided in settings'
        assert settings.secret_key_token_generator, '`SECRET_KEY_TOKEN_GENERATOR` must be provided in settings'
        self._secret = secret_key
        self._token_expired_time = token_expired_timeout
        self.algorithm = self.algorithm or 'sha256'

    @property
    def secret(self) -> None | str:
        return self._secret

    def make_token(self, user) -> str:
        """
        Return a token that can be used once to do a password reset
        for or activate account of the given `user`.
        """
        return self._make_token_with_timestamp(
            user=user,
            timestamp=self._num_seconds(self._now()),
            secret=self.secret,
        )

    def check_token(self, user, token: str) -> bool:
        """
        Check that a `token` is correct for a given `user`.
        """
        if not all([user, token]):
            return False
        # Parse the token
        try:
            timestamp_base36, _ = token.split('-')
        except ValueError:
            return False

        try:
            ts = base36decode(timestamp_base36)
        except ValueError:
            return False

        # check that the timestamp/uid has not been tampered with
        if not compare_digest(
                self._make_token_with_timestamp(user, ts, self.secret).encode('utf-8'),
                token.encode('utf-8'),
        ):
            return False

        # check the timestamp is within limit
        if (self._num_seconds(self._now()) - ts) > self._token_expired_time:
            return False

        return True

    def _make_token_with_timestamp(self, user, timestamp: int, secret: str) -> str:
        """
        Make token with passed `timestamp` which is number of seconds since 2001-1-1 and
        converted to base36.
        Returns string separate with hyphen contains with encoded to base36 `timestamp`
        and hash with `user`'s data converted to hexadecimal.
        """
        timestamp_base36 = base36encode(timestamp)
        hash_string = hmac.new(
            key=hashlib.sha256(self.key_salt.encode('utf-8') + secret.encode('utf-8')).digest(),
            msg=self._make_hash_value(user, timestamp).encode('utf-8'),
            digestmod=hashlib.sha256,
        ).hexdigest()[::2]  # limit to shorten the URL
        return f'{timestamp_base36}-{hash_string}'

    def _make_hash_value(self, user, timestamp: int) -> str:
        """
        Hash the user's primary key, email (if available), and some user state
        that's sure to change after a password reset or activate own account
        to produce a token that is invalidated when it's used:
        1. The `hashed_password` field or will change upon a password reset (even if the
           same password is chosen, due to password salting).
        2. The `last_login` field will usually be updated very shortly after
           a password reset.
        3. The `is_active` field will be updated after user will activate its account.
        Failing those things, settings.TOKEN_EXPIRED_TIMEOUT eventually
        invalidates the token.

        Running this data through `hmac.new()` prevents password cracking
        attempts using the reset token, provided the secret isn't compromised.
        """
        # Truncate microseconds so that tokens are consistent even if the
        # database doesn't support microseconds.
        login_timestamp = (
            ''
            if user.last_login is None
            else user.last_login.replace(microsecond=0, tzinfo=None)
        )
        return f'{user.id}{user.hashed_password}{login_timestamp}{timestamp}{user.email}{user.is_active}'

    def _num_seconds(self, dt) -> int:
        return int((dt - datetime(2001, 1, 1)).total_seconds())

    def _now(self) -> datetime:
        return datetime.now()


token_generator = LimitedLifeTokenGenerator(
    secret_key=settings.secret_key_token_generator,
    token_expired_timeout=settings.token_expired_timeout
)
