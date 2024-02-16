from typing import Union

from common.security import get_password_hash
from common.tasks import invalidate_endpoint_cache


class CrudManager:
    """
    Class provides opportunity to make CRUD requests:
    * update - POST,
    * partial_update - PATCH,
    * update - PUT,
    * destroy - DELETE.
    """

    def __init__(self, db, model_class) -> None:
        self._session = db
        self._model_class = model_class

    def __repr__(self):
        return f'Model: {self._model_class}, session: {self._session.bind.engine}'

    async def retrieve(self, criterion: Union[tuple, None] = None, many: bool = False,
                       skip: int = 0, limit: int = 100, order_by: str = 'id', **kwargs):
        """
        Make `get` request.
        * criterion - criterion to filter (where) records in output,
        * many - indicates whether output should contain one or more records,
        * skip - number of records at the start to skip in output,
        * limit - number of records at the end to limit in output,
        * order_by - criterion to order output records.
        """
        if many and not criterion:
            return self._session.query(self._model_class).order_by(order_by).offset(skip).limit(limit).all()
        if many and criterion:
            return self._session.query(self._model_class).filter(
                criterion).order_by(order_by).offset(skip).limit(limit).all()

        # if needed single record
        return self._session.query(self._model_class).filter(criterion).first()

    async def update(self, instance, data_to_update: dict, *args, **kwargs):
        """
        Make `put` request.
        """
        self._session.query(self._model_class).filter(self._model_class.id == instance.id).update(data_to_update)
        self._session.commit()
        self._session.refresh(instance)
        self._send_request_to_cache_invalidation(namespace=self._model_class.__tablename__, request_method='get')
        return instance

    async def partial_update(self, instance, data_to_update: dict, *args, **kwargs):
        """
        Make `patch` request in order to update `instance` with `data_to_update` data.
        User can pass `update_password` key with `True` to update password.
        """
        if 'update_password' in kwargs:
            data_to_update['hashed_password'] = data_to_update.get('password')
            data_to_update.pop('password')

        self._session.query(self._model_class).filter(self._model_class.id == instance.id).update(data_to_update)
        self._session.commit()
        self._session.refresh(instance)
        self._send_request_to_cache_invalidation(namespace=self._model_class.__tablename__, request_method='get')
        return instance

    async def create(self, instance_data: dict, *args, **kwargs):
        """
        Make `post` request and create instance of `self._model_class` with `instance_data`.
        User can pass `set_password` key with `True` to set account password.
        """
        if ('set_password' and 'password') in kwargs:
            hashed_password = self._create_password_hash(kwargs['password'])
            instance_data['hashed_password'] = hashed_password

        instance = self._model_class(**instance_data)
        self._session.add(instance)
        self._session.commit()
        self._session.refresh(instance)
        self._send_request_to_cache_invalidation(namespace=self._model_class.__tablename__, request_method='get')
        return instance

    async def destroy(self, instance) -> None:
        """
        Make `delete` request to remove `instance`.
        """
        self._session.query(self._model_class).filter(self._model_class.id == instance.id).delete()
        self._session.commit()
        self._send_request_to_cache_invalidation(namespace=self._model_class.__tablename__, request_method='get')

    @staticmethod
    def _create_password_hash(plain_password: str) -> str:
        """
        Needed for create hash value from plain text password.
        """
        return get_password_hash(plain_password)

    @staticmethod
    def _send_request_to_cache_invalidation(namespace: str, request_method: str) -> None:
        """
        Call task for invalidating cache on results which could be obtained after
        updated, created or deleted data in database and thus could be incorrect.
        """
        invalidate_endpoint_cache.delay(namespace, request_method)
