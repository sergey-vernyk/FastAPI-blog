"""Alter table 'users'. Add columns 'image' and 'about'.

Revision ID: 62818de011e2
Revises: c1e28ea2155c
Create Date: 2023-12-20 20:47:30.502305

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '62818de011e2'
down_revision: Union[str, None] = 'c1e28ea2155c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('image', sa.String, nullable=True))
    op.add_column('users', sa.Column('about', sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'image')
    op.drop_column('users', 'about')
