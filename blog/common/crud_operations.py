from abc import ABC, abstractmethod
from typing import Union

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from common.security import get_password_hash
from common.tasks import invalidate_endpoint_cache


class CrudManagerAbstract(ABC):
    """
    Class for providing CRUD operations:
    * update - POST,
    * partial_update - PATCH,
    * update - PUT,
    * destroy - DELETE.
    """

    @abstractmethod
    def __init__(self, db: Union[Session, AsyncSession], model_class, *args, **kwargs):
        self._session = db
        self._model_class = model_class
        raise NotImplemented('Method `__init__` is not implemented in the child class.')

    def __repr__(self):
        return f'Model: {self._model_class}, session: {self._session.bind.engine}'

    @abstractmethod
    async def retrieve(self, criterion: Union[tuple, None] = None, many: bool = False,
                       skip: int = 0, limit: int = 100, order_by: str = 'id', **kwargs):
        """
        Performs `get` request.
        * criterion - criterion to filter (where) records in output,
        * many - indicates whether output should contain one or more records,
        * skip - number of records at the start to skip in output,
        * limit - number of records at the end to limit in output,
        * order_by - criterion to order output records.
        """
        raise NotImplementedError('Method `retrieve` is not implemented in the child class.')

    @abstractmethod
    async def update(self, instance, data_to_update: dict, *args, **kwargs):
        """
        Performs `put` request and return updated `instance`.
        """
        raise NotImplementedError('Method `update` is not implemented in the child class.')

    @abstractmethod
    async def partial_update(self, instance, data_to_update: dict, *args, **kwargs):
        """
        Performs `patch` request in order to update `instance` with `data_to_update` data.
        User can pass `update_password` key with `True` to update password.
        Returns updated `instance`.
        """
        raise NotImplementedError('Method `partial_update` is not implemented the in child class.')

    @abstractmethod
    async def create(self, instance_data: dict, *args, **kwargs):
        """
        Performs `post` request and create instance of `self._model_class` with `instance_data`.
        User can pass `set_password` key with `True` to set password.
        """
        raise NotImplementedError('Method `create` is not implemented the in the child class.')

    @abstractmethod
    async def destroy(self, instance) -> None:
        """
        Performs `delete` request to remove `instance`.
        """
        raise NotImplementedError('Method `destroy` is not implemented the in the child class.')

    @staticmethod
    @abstractmethod
    def _create_password_hash(plain_password: str) -> str:
        """
        Needed for create hash value from plain text password.
        """
        raise NotImplementedError('Static method `create_password_hash` is not implemented in the child class.')


class CrudManager(CrudManagerAbstract):

    def __init__(self, db: Session, model_class) -> None:
        self._session = db
        self._model_class = model_class

    async def retrieve(self, criterion: Union[tuple, None] = None, many: bool = False,
                       skip: int = 0, limit: int = 100, order_by: str = 'id', **kwargs):
        if many and not criterion:
            return self._session.query(self._model_class).order_by(order_by).offset(skip).limit(limit).all()
        if many and criterion:
            return self._session.query(self._model_class).filter(
                criterion).order_by(order_by).offset(skip).limit(limit).all()

        # if needed single record
        return self._session.query(self._model_class).filter(criterion).first()

    async def update(self, instance, data_to_update: dict, *args, **kwargs):
        self._session.query(self._model_class).filter(self._model_class.id == instance.id).update(data_to_update)
        self._session.commit()
        self._session.refresh(instance)
        self._send_request_to_cache_invalidation(namespace=self._model_class.__tablename__, request_method='get')
        return instance

    async def partial_update(self, instance, data_to_update: dict, *args, **kwargs):
        if 'update_password' in kwargs:
            data_to_update['hashed_password'] = data_to_update.get('password')
            data_to_update.pop('password')

        self._session.query(self._model_class).filter(self._model_class.id == instance.id).update(data_to_update)
        self._session.commit()
        self._session.refresh(instance)
        self._send_request_to_cache_invalidation(namespace=self._model_class.__tablename__, request_method='get')
        return instance

    async def create(self, instance_data: dict, *args, **kwargs):
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


class CrudManagerAsync(CrudManagerAbstract):

    def __init__(self, db: AsyncSession, model_class) -> None:
        self._session = db
        self._model_class = model_class

    async def retrieve(self, criterion: Union[tuple, None] = None, many: bool = False,
                       skip: int = 0, limit: int = 100, order_by: str = 'id', **kwargs):
        if many and not criterion:
            statement = select(self._model_class).order_by(order_by).offset(skip).limit(limit)
        elif many and criterion:
            statement = select(self._model_class).where(criterion).order_by(order_by).offset(skip).limit(limit)
        else:
            # if needed single record
            statement = select(self._model_class).where(criterion)

        buffered_result = await self._session.execute(statement)
        return buffered_result.scalars() if many else buffered_result.scalar()

    async def update(self, instance, data_to_update: dict, *args, **kwargs):
        statement = (
            update(self._model_class.__table__)
            .where(self._model_class.id == instance.id)
            .values(**data_to_update)
        )
        await self._session.execute(statement)
        await self._session.commit()
        await self._session.refresh(instance)
        self._send_request_to_cache_invalidation(namespace=self._model_class.__tablename__, request_method='get')
        return instance

    async def partial_update(self, instance, data_to_update: dict, *args, **kwargs):
        if 'update_password' in kwargs:
            data_to_update['hashed_password'] = data_to_update.get('password')
            data_to_update.pop('password')

        statement = (
            update(self._model_class.__table__)
            .where(self._model_class.id == instance.id)
            .values(**data_to_update)
        )
        await self._session.execute(statement)
        await self._session.commit()
        await self._session.refresh(instance)
        self._send_request_to_cache_invalidation(namespace=self._model_class.__tablename__, request_method='get')
        return instance

    async def destroy(self, instance) -> None:
        statement = delete(self._model_class.__table__).where(self._model_class.id == instance.id)
        await self._session.execute(statement)
        await self._session.commit()
        self._send_request_to_cache_invalidation(namespace=self._model_class.__tablename__, request_method='get')

    async def create(self, instance_data: dict, *args, **kwargs):
        if ('set_password' and 'password') in kwargs:
            hashed_password = self._create_password_hash(kwargs['password'])
            instance_data['hashed_password'] = hashed_password

        instance = self._model_class(**instance_data)
        self._session.add(instance)
        await self._session.commit()
        await self._session.refresh(instance)
        self._send_request_to_cache_invalidation(namespace=self._model_class.__tablename__, request_method='get')
        return instance

    @staticmethod
    def _send_request_to_cache_invalidation(namespace: str, request_method: str) -> None:
        """
        Call task for invalidating cache on results which could be obtained after
        updated, created or deleted data in database and thus could be incorrect.
        """
        invalidate_endpoint_cache.delay(namespace, request_method)

    @staticmethod
    def _create_password_hash(plain_password: str) -> str:
        return get_password_hash(plain_password)
