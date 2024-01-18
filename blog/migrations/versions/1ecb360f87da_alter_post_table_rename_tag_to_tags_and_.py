"""Alter Post table. Rename 'tag' to 'tags' and change size of 'tags' column.

Revision ID: 1ecb360f87da
Revises: 46d3ec488cb5
Create Date: 2023-11-29 16:20:36.424522

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ecb360f87da'
down_revision: Union[str, None] = '46d3ec488cb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('posts', 'tag', new_column_name='tags', type_=sa.String(100))


def downgrade() -> None:
    op.alter_column('posts', 'tags', new_column_name='tag', type_=sa.String(50))
