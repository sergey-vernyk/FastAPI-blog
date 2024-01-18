"""Alter table 'users'. Add field 'social_media_links'.

Revision ID: a247b82d042e
Revises: aba9728e079c
Create Date: 2024-01-18 17:30:05.332326

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a247b82d042e'
down_revision: Union[str, None] = 'aba9728e079c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('social_media_links', sa.ARRAY(sa.String(2083)), default=[], nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'social_media_links')
