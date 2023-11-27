"""Add a column role

Revision ID: b66ce1fd1d33
Revises: dd6883c276e7
Create Date: 2023-11-26 18:09:17.772553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b66ce1fd1d33'
down_revision: Union[str, None] = 'dd6883c276e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('role', sa.String(15)))


def downgrade() -> None:
    op.drop_column('users', 'role')
