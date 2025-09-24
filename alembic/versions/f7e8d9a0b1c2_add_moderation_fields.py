"""Add moderation fields to products and pawah_projects

Revision ID: f7e8d9a0b1c2
Revises: f1a2b3c4d5e6
Create Date: 2025-09-24 13:28:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7e8d9a0b1c2'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    # Use SQLite PRAGMA to introspect existing columns for idempotency
    try:
        prod_cols = {row[1] for row in bind.exec_driver_sql("PRAGMA table_info('products')").fetchall()}
    except Exception:
        prod_cols = set()
    with op.batch_alter_table('products') as batch_op:
        if 'rejection_reason' not in prod_cols:
            batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        if 'reviewed_by_id' not in prod_cols:
            batch_op.add_column(sa.Column('reviewed_by_id', sa.Integer(), nullable=True))
        if 'reviewed_at' not in prod_cols:
            batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(), nullable=True))
        if 'approved_at' not in prod_cols:
            batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))

    # pawah_projects moderation fields (idempotent)
    try:
        pawah_cols = {row[1] for row in bind.exec_driver_sql("PRAGMA table_info('pawah_projects')").fetchall()}
    except Exception:
        pawah_cols = set()
    with op.batch_alter_table('pawah_projects') as batch_op:
        if 'rejection_reason' not in pawah_cols:
            batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        if 'reviewed_by_id' not in pawah_cols:
            batch_op.add_column(sa.Column('reviewed_by_id', sa.Integer(), nullable=True))
        if 'reviewed_at' not in pawah_cols:
            batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(), nullable=True))
        if 'approved_at' not in pawah_cols:
            batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('pawah_projects') as batch_op:
        batch_op.drop_column('approved_at')
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('reviewed_by_id')
        batch_op.drop_column('rejection_reason')

    with op.batch_alter_table('products') as batch_op:
        batch_op.drop_column('approved_at')
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('reviewed_by_id')
        batch_op.drop_column('rejection_reason')
