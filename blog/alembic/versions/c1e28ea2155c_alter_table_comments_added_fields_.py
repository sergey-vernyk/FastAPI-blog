"""Alter table 'comments'. Added fields 'created' and 'updated'.

Revision ID: c1e28ea2155c
Revises: c03e1b46d0b1
Create Date: 2023-12-17 21:56:21.900516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1e28ea2155c'
down_revision: Union[str, None] = 'c03e1b46d0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('comments', sa.Column('created', sa.DateTime))
    op.add_column('comments', sa.Column('updated', sa.DateTime))


def downgrade() -> None:
    op.drop_column('comments', 'created')
    op.drop_column('comments', 'updated')
