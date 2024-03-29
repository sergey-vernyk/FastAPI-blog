"""Alter table Comment, Category, Post. Added 'ondelete' param and 'passive_deletes' param.

Revision ID: 10cca17755bc
Revises: 4b65546e1ace
Create Date: 2024-02-14 14:18:39.320428

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '10cca17755bc'
down_revision: Union[str, None] = '4b65546e1ace'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('fk_posts_comments', 'comments', type_='foreignkey')
    op.create_foreign_key(None, 'comments', 'posts', ['post_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('fk_posts_postcategories', 'posts', type_='foreignkey')
    op.create_foreign_key(None, 'posts', 'postcategories', ['category_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'posts', type_='foreignkey')
    op.create_foreign_key('fk_posts_postcategories', 'posts', 'postcategories', ['category_id'], ['id'])
    op.drop_constraint(None, 'comments', type_='foreignkey')
    op.create_foreign_key('fk_posts_comments', 'comments', 'posts', ['post_id'], ['id'])
    # ### end Alembic commands ###
