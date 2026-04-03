"""Add settings table for global configuration

Revision ID: 003
Revises: 002
Create Date: 2024-12-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create settings table
    op.create_table(
        'settings',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )
    
    # Make filter_prompt nullable in jobsource table
    with op.batch_alter_table('jobsource') as batch_op:
        batch_op.alter_column(
            'filter_prompt',
            existing_type=sa.String(),
            nullable=True,
        )


def downgrade() -> None:
    # Make filter_prompt required again
    with op.batch_alter_table('jobsource') as batch_op:
        batch_op.alter_column(
            'filter_prompt',
            existing_type=sa.String(),
            nullable=False,
        )
    
    # Drop settings table
    op.drop_table('settings')
