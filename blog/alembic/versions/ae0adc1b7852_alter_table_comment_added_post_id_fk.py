"""Alter table Comment: added 'post_id' fk. 

Revision ID: ae0adc1b7852
Revises: 6c3a2a2ea353
Create Date: 2023-12-03 22:20:36.334652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae0adc1b7852'
down_revision: Union[str, None] = '6c3a2a2ea353'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('comments', sa.Column('post_id', sa.Integer))
    op.create_foreign_key('fk_posts_comments',
                          'comments',
                          'posts',
                          ['post_id'],
                          ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_post_comment', 'comments', type_='foreignkey')
    op.drop_column('comments', 'post_id')
