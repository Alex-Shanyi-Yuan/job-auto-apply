"""add job stage tracking

Revision ID: 005
Revises: 004
Create Date: 2024-04-04
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from datetime import datetime, timezone

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def upgrade():
    # Create jobstage table
    op.create_table(
        'jobstage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('stage_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['job.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id', 'stage_name', name='uq_job_stage')
    )
    
    # Add rejection fields to job table
    op.add_column('job', sa.Column('rejection_stage', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('job', sa.Column('rejection_reason', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    
    # Migrate existing job data
    connection = op.get_bind()
    
    # Get all jobs with non-suggested status
    jobs = connection.execute(
        sa.text("SELECT id, status, created_at FROM job WHERE status != 'suggested'")
    ).fetchall()
    
    for job in jobs:
        job_id, status, created_at = job
        
        if status == 'applied':
            # Create 'applied' stage
            connection.execute(
                sa.text("""
                    INSERT INTO jobstage (job_id, stage_name, completed_at, created_at, updated_at)
                    VALUES (:job_id, 'applied', :completed_at, :now, :now)
                """),
                {"job_id": job_id, "completed_at": created_at, "now": utcnow()}
            )
            # Update status to 'active'
            connection.execute(
                sa.text("UPDATE job SET status = 'active' WHERE id = :job_id"),
                {"job_id": job_id}
            )
        
        elif status == 'interviewing':
            # Create 'applied' and 'interview' stages
            for stage in ['applied', 'interview']:
                connection.execute(
                    sa.text("""
                        INSERT INTO jobstage (job_id, stage_name, completed_at, created_at, updated_at)
                        VALUES (:job_id, :stage, :completed_at, :now, :now)
                    """),
                    {"job_id": job_id, "stage": stage, "completed_at": created_at, "now": utcnow()}
                )
            connection.execute(
                sa.text("UPDATE job SET status = 'active' WHERE id = :job_id"),
                {"job_id": job_id}
            )
        
        elif status == 'offer':
            # Create all 4 stages
            for stage in ['applied', 'oa', 'interview', 'offer']:
                connection.execute(
                    sa.text("""
                        INSERT INTO jobstage (job_id, stage_name, completed_at, created_at, updated_at)
                        VALUES (:job_id, :stage, :completed_at, :now, :now)
                    """),
                    {"job_id": job_id, "stage": stage, "completed_at": created_at, "now": utcnow()}
                )
            connection.execute(
                sa.text("UPDATE job SET status = 'active' WHERE id = :job_id"),
                {"job_id": job_id}
            )
        
        # Keep 'rejected', 'dismissed', 'failed' status unchanged


def downgrade():
    # Revert status changes (best effort)
    connection = op.get_bind()
    
    # Jobs with 'active' status and stages -> revert to 'applied' or 'interviewing'
    active_jobs = connection.execute(
        sa.text("SELECT DISTINCT job_id FROM jobstage WHERE stage_name = 'interview'")
    ).fetchall()
    
    for job in active_jobs:
        connection.execute(
            sa.text("UPDATE job SET status = 'interviewing' WHERE id = :job_id"),
            {"job_id": job[0]}
        )
    
    # Remaining active jobs -> revert to 'applied'
    connection.execute(
        sa.text("UPDATE job SET status = 'applied' WHERE status = 'active'")
    )
    
    # Drop columns and table
    op.drop_column('job', 'rejection_reason')
    op.drop_column('job', 'rejection_stage')
    op.drop_table('jobstage')