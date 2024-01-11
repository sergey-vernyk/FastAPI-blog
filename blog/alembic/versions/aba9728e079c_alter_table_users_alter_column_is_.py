"""Alter table 'users'. Alter column 'is_active' to False by default.

Revision ID: aba9728e079c
Revises: cd4877bdf613
Create Date: 2024-01-05 19:57:19.891066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aba9728e079c'
down_revision: Union[str, None] = 'cd4877bdf613'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', sa.Column('is_active', sa.Boolean, default=False))


def downgrade() -> None:
    op.alter_column('users', sa.Column('is_active', sa.Boolean, default=True))
