"""Alter table User: add 'gender' column. Alter tables 'likes', 'dislikes': add primary kays. Alter table Comment: add column 'owner_id'.

Revision ID: 31ca0e5ddb61
Revises: ae0adc1b7852
Create Date: 2023-12-04 13:33:03.318006

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31ca0e5ddb61'
down_revision: Union[str, None] = 'ae0adc1b7852'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('likes', sa.Column('id', sa.Integer, primary_key=True, index=True))
    op.add_column('dislikes', sa.Column('id', sa.Integer, primary_key=True, index=True))
    op.add_column('comments', sa.Column('owner_id', sa.Integer))
    op.add_column('users', sa.Column('gender', sa.String(6), nullable=True))

    op.create_foreign_key('comments_users_fk',
                          'comments',
                          'users',
                          ['owner_id'],
                          ['id'])


def downgrade() -> None:
    op.drop_column('likes', 'id')
    op.drop_column('dislikes', 'id')
    op.drop_constraint('comments_users_fk', 'comments', type_='foreignkey')
    op.drop_column('comments', 'owner_id')
    op.drop_column('users', 'gender')
