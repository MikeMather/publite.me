"""add_home_page_id_to_settings

Revision ID: d6851f10fb6b
Revises: f79f4aa97c37
Create Date: 2025-03-02 19:58:47.391973

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6851f10fb6b"
down_revision: Union[str, None] = "f79f4aa97c37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a new settings table with the home_page_id column
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("home_page_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_settings_home_page", "posts", ["home_page_id"], ["id"]
        )


def downgrade() -> None:
    # Remove the home_page_id column from settings table
    with op.batch_alter_table("settings", schema=None) as batch_op:
        batch_op.drop_constraint("fk_settings_home_page", type_="foreignkey")
        batch_op.drop_column("home_page_id")
