"""Create audit_logs table

Revision ID: a1b2c3d4e5f6
Revises: f7e8d9a0b1c2
Create Date: 2025-09-24 14:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f7e8d9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    try:
        cols = {row[1] for row in bind.exec_driver_sql("PRAGMA table_info('audit_logs')").fetchall()}
        table_exists = bool(cols)
    except Exception:
        table_exists = False

    if not table_exists:
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('entity_type', sa.String(length=30), nullable=False),
            sa.Column('entity_id', sa.Integer(), nullable=False),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('old_status', sa.String(length=50), nullable=True),
            sa.Column('new_status', sa.String(length=50), nullable=True),
            sa.Column('actor_id', sa.Integer(), nullable=True),
            sa.Column('meta', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        # Helpful index on entity for fast lookups
        op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])


def downgrade() -> None:
    try:
        op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    except Exception:
        pass
    op.drop_table('audit_logs')
