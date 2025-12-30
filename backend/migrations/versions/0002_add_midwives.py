"""add midwives table

Revision ID: 0002_add_midwives
Revises: 0001_initial
Create Date: 2024-12-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_add_midwives'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'midwives',
        sa.Column('midwife_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('midwife_id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_midwives_email', 'midwives', ['email'])


def downgrade() -> None:
    op.drop_index('ix_midwives_email', table_name='midwives')
    op.drop_table('midwives')
