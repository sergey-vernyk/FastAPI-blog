"""Alter table 'users'. Add columns 'last_login', 'date_joined', 'rating'.

Revision ID: cd4877bdf613
Revises: 62818de011e2
Create Date: 2024-01-05 19:18:45.561577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd4877bdf613'
down_revision: Union[str, None] = '62818de011e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('date_joined', sa.DateTime(timezone=True), nullable=False))
    op.add_column('users', sa.Column('rating', sa.Integer, sa.CheckConstraint('rating >= 0 AND rating <= 100'), default=0))


def downgrade() -> None:
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'date_joined')
    op.drop_column('users', 'rating')
