"""Add Post and  Category models.

Revision ID: b183c1fd2c1a
Revises: 997324058009
Create Date: 2023-11-28 20:56:15.642156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b183c1fd2c1a'
down_revision: Union[str, None] = '997324058009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'posts',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('title', sa.String(512), nullable=False, unique=True),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('tag', sa.String(50), nullable=False),
        sa.Column('category_id', sa.Integer),
        sa.Column('owner_id', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('rating', sa.SmallInteger),
        sa.Column('is_publish', sa.Boolean, default=False),
        sa.Column('created', sa.DateTime),
        sa.Column('updated', sa.DateTime)
    )

    op.create_table(
        'postcategories',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String(50), unique=True),
    )

    op.create_foreign_key('fk_posts_postcategories',
                          'posts',
                          'postcategories',
                         ['category_id'],
                         ['id'])


def downgrade() -> None:
    op.drop_table('posts')
    op.drop_table('postcategories')
