"""add unique index on job.url

Guarantees a job URL maps to at most one row, preventing duplicates from
concurrent scans or an apply-vs-scan overlap. Existing duplicate URLs (if any)
are collapsed to the lowest id before the index is created.

Revision ID: 007
Revises: 006
Create Date: 2026-05-31
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect, text


revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_job_url_unique"


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return any(ix["name"] == index_name for ix in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    # Collapse any pre-existing duplicate URLs (keep the lowest id) so the
    # unique index can be created. Valid on both SQLite and PostgreSQL.
    bind.execute(text("DELETE FROM job WHERE id NOT IN (SELECT MIN(id) FROM job GROUP BY url)"))
    if not _has_index("job", INDEX_NAME):
        op.create_index(INDEX_NAME, "job", ["url"], unique=True)


def downgrade() -> None:
    if _has_index("job", INDEX_NAME):
        op.drop_index(INDEX_NAME, table_name="job")
