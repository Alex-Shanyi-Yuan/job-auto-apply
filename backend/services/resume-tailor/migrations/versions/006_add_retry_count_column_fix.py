"""add retry_count column fix

Revision ID: 006
Revises: 77efc08f45fb
Create Date: 2026-04-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "77efc08f45fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    if not _has_column("job", "retry_count"):
        op.add_column(
            "job",
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _has_column("job", "retry_count"):
        op.drop_column("job", "retry_count")
