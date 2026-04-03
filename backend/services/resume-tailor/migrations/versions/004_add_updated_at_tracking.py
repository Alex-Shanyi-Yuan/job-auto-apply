"""add updated_at tracking for mutable tables

Revision ID: 004
Revises: 003
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobsource', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('job', sa.Column('updated_at', sa.DateTime(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE jobsource SET updated_at = COALESCE(last_scraped_at, created_at, CURRENT_TIMESTAMP)"
        )
    )
    op.execute(sa.text("UPDATE job SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP)"))

    with op.batch_alter_table('jobsource') as batch_op:
        batch_op.alter_column(
            'updated_at',
            existing_type=sa.DateTime(),
            nullable=False,
        )

    with op.batch_alter_table('job') as batch_op:
        batch_op.alter_column(
            'updated_at',
            existing_type=sa.DateTime(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('job') as batch_op:
        batch_op.drop_column('updated_at')

    with op.batch_alter_table('jobsource') as batch_op:
        batch_op.drop_column('updated_at')
