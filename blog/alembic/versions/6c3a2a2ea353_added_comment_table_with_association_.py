"""Added Comment table with association tables 'likes' and 'dislikes'.

Revision ID: 6c3a2a2ea353
Revises: 1ecb360f87da
Create Date: 2023-12-03 18:42:46.093481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c3a2a2ea353'
down_revision: Union[str, None] = '1ecb360f87da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('body', sa.String(600), nullable=False),
    )

    op.create_table(
        'likes',
        sa.Column('comment_id', sa.Integer, sa.ForeignKey('comments.id'), nullable=False),
        sa.Column('post_id', sa.Integer, sa.ForeignKey('posts.id'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    )

    op.create_table(
        'dislikes',
        sa.Column('comment_id', sa.Integer, sa.ForeignKey('comments.id'), nullable=False),
        sa.Column('post_id', sa.Integer, sa.ForeignKey('posts.id'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('likes')
    op.drop_table('dislikes')
    op.drop_table('comments')
