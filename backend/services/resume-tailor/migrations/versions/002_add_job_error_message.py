"""Add error_message column to job table

Revision ID: 002
Revises: 001
Create Date: 2024-12-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add error_message column to job table
    op.add_column('job', sa.Column('error_message', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove error_message column from job table
    op.drop_column('job', 'error_message')
