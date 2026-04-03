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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('jobsource'):
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

    if not inspector.has_table('job'):
        op.create_table(
            'job',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('company', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('requirements', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('pdf_path', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('score', sa.Integer(), nullable=True),
            sa.Column('source_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['source_id'], ['jobsource.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('url')
        )
    else:
        existing_columns = {col['name'] for col in inspector.get_columns('job')}

        if 'score' not in existing_columns:
            op.add_column('job', sa.Column('score', sa.Integer(), nullable=True))
        if 'source_id' not in existing_columns:
            op.add_column('job', sa.Column('source_id', sa.Integer(), nullable=True))

        existing_fks = {
            fk.get('name') for fk in inspector.get_foreign_keys('job') if fk.get('name')
        }
        if 'fk_job_source_id' not in existing_fks:
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
