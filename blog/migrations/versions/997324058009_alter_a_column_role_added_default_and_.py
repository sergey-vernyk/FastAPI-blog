"""Alter a column role. Added default and nullable values

Revision ID: 997324058009
Revises: b66ce1fd1d33
Create Date: 2023-11-26 19:32:17.284137

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '997324058009'
down_revision: Union[str, None] = 'b66ce1fd1d33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'role', nullable=False, default='regular-user')


def downgrade() -> None:
    op.alter_column('users', 'role', nullable=True, default='')
