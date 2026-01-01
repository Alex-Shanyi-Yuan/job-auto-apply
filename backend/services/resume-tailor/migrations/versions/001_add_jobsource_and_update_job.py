"""add jobsource table and update job table

Revision ID: 001
Revises: 
Create Date: 2024-12-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create JobSource table
    op.create_table(
        'jobsource',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('filter_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('last_scraped_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add new columns to Job table
    op.add_column('job', sa.Column('score', sa.Integer(), nullable=True))
    op.add_column('job', sa.Column('source_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_job_source_id',
        'job', 'jobsource',
        ['source_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_job_source_id', 'job', type_='foreignkey')
    
    # Remove columns from Job table
    op.drop_column('job', 'source_id')
    op.drop_column('job', 'score')
    
    # Drop JobSource table
    op.drop_table('jobsource')
