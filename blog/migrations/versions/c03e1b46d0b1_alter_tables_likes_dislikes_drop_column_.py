"""Alter tables 'likes', 'dislikes': drop column 'post_id'.

Revision ID: c03e1b46d0b1
Revises: 31ca0e5ddb61
Create Date: 2023-12-04 16:47:01.658784

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c03e1b46d0b1'
down_revision: Union[str, None] = '31ca0e5ddb61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('likes_post_id_fkey', 'likes', type_='foreignkey')
    op.drop_constraint('dislikes_post_id_fkey', 'dislikes', type_='foreignkey')
    op.drop_column('likes', 'post_id')
    op.drop_column('dislikes', 'post_id')


def downgrade() -> None:
    op.add_column('likes', sa.Column('post_id', sa.Integer))
    op.add_column('dislikes', sa.Column('post_id', sa.Integer))
    op.create_foreign_key('likes_post_id_fkey',
                          'likes',
                          'posts',
                          ['post_id'],
                          ['id'])
    op.create_foreign_key('dislikes_post_id_fkey',
                          'dislikes',
                          'posts',
                          ['post_id'],
                          ['id'])
