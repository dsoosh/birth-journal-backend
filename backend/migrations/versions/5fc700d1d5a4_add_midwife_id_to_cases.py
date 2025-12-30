"""add_midwife_id_to_cases

Revision ID: 5fc700d1d5a4
Revises: 0002_add_midwives
Create Date: 2025-12-30 12:44:10.348325

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5fc700d1d5a4'
down_revision = '0002_add_midwives'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('cases', sa.Column('midwife_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_cases_midwife_id', 'cases', 'midwives', ['midwife_id'], ['midwife_id'])


def downgrade() -> None:
    op.drop_constraint('fk_cases_midwife_id', 'cases', type_='foreignkey')
    op.drop_column('cases', 'midwife_id')
