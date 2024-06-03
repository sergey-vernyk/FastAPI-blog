"""Alter User table. Added unique parameter to username field.

Revision ID: 46d3ec488cb5
Revises: b183c1fd2c1a
Create Date: 2023-11-29 14:59:22.610905

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '46d3ec488cb5'
down_revision: Union[str, None] = 'b183c1fd2c1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_username', 'users', ['username'])


def downgrade() -> None:
    op.drop_constraint('uq_username', 'users', type_='unique')
