"""Alter tables Comment, likes_table, dislikes_table.  Added 'ondelete' param and 'passive_deletes' param.

Revision ID: e854914ad7c9
Revises: 10cca17755bc
Create Date: 2024-02-14 14:27:19.782113

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e854914ad7c9'
down_revision: Union[str, None] = '10cca17755bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('dislikes_user_id_fkey', 'dislikes', type_='foreignkey')
    op.drop_constraint('dislikes_comment_id_fkey', 'dislikes', type_='foreignkey')
    op.create_foreign_key(None, 'dislikes', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'dislikes', 'comments', ['comment_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('likes_user_id_fkey', 'likes', type_='foreignkey')
    op.drop_constraint('likes_comment_id_fkey', 'likes', type_='foreignkey')
    op.create_foreign_key(None, 'likes', 'comments', ['comment_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'likes', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'likes', type_='foreignkey')
    op.drop_constraint(None, 'likes', type_='foreignkey')
    op.create_foreign_key('likes_comment_id_fkey', 'likes', 'comments', ['comment_id'], ['id'])
    op.create_foreign_key('likes_user_id_fkey', 'likes', 'users', ['user_id'], ['id'])
    op.drop_constraint(None, 'dislikes', type_='foreignkey')
    op.drop_constraint(None, 'dislikes', type_='foreignkey')
    op.create_foreign_key('dislikes_comment_id_fkey', 'dislikes', 'comments', ['comment_id'], ['id'])
    op.create_foreign_key('dislikes_user_id_fkey', 'dislikes', 'users', ['user_id'], ['id'])
    # ### end Alembic commands ###