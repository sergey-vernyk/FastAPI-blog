import logging
from functools import wraps
from inspect import iscoroutinefunction
from pathlib import Path
from typing import Any, Callable, Literal

from fastapi.exceptions import HTTPException

from config import get_settings

settings = get_settings()

FORMATTER_FORMAT = (
    '%(asctime)s  Module: [%(name)s]  Level: [%(levelname)s]  Message: [%(message)s] Extra params: [%(extra)s]'
)
FORMATTER_DATA_FORMAT = '%d/%m/%Y %H:%M:%S'

# define parent directory path for the directory `static` (for possibility using relative path)
PARENT_DIR_PATH = str(Path(__file__).resolve().parent.parent)

LOGS_DIRECTORY = ''
if settings.dev_or_prod == 'dev':
    LOGS_DIRECTORY = f'{PARENT_DIR_PATH}/loggers'
elif settings.dev_or_prod == 'prod':
    LOGS_DIRECTORY = '/vol/logs'


def set_endpoint_logger(level: Literal['debug', 'info', 'warning', 'error', 'critical'],
                        module_name: str, endpoint_path: str) -> Callable:
    """
    Set up logger which used in router endpoints.
    - level: severity of an error.
    - module_name: module where the logger has been defined.
    - endpoint path: endpoint path which the logger is monitoring.
    """
    logger = logging.getLogger(module_name)
    # get logger method which response for passed `level`
    logger_level = getattr(logger, level, None)
    if logger_level is None:
        raise ValueError(f'Passed logging level `{level}` does not allowed.')
    extra_data = None  # data to add to log

    def wrapper(func: Callable):
        @wraps(func)
        async def inner(*args, **kwargs) -> Any:
            nonlocal extra_data
            try:
                if iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except HTTPException as http_ex:
                logger.setLevel(level.upper())
                kwargs.update(endpoint_path=endpoint_path)
                extra_data = exclude_unnecessary_data(kwargs)
                logger_level(msg=http_ex.detail, exc_info=True, extra={'extra': extra_data})
                raise http_ex
            except Exception as common_ex:
                logger.setLevel(logging.ERROR)
                kwargs.update(endpoint_path=endpoint_path)
                extra_data = exclude_unnecessary_data(kwargs)
                logger.error(msg=common_ex.args, exc_info=True, extra={'extra': extra_data})
                raise common_ex

        return inner

    return wrapper


def exclude_unnecessary_data(data: dict) -> dict:
    """
    Returns `data` without any sensitive and unnecessary data.
    """
    unnecessary_data = (
        'password',
        'uidb64',
        'token',
        'login_data',
        'reset_pswd_form',
        'uid_pass',
        'update_data',
        'settings',
        'db',
        'request',
    )
    return dict(filter(lambda d: d[0] not in unnecessary_data, data.items()))
