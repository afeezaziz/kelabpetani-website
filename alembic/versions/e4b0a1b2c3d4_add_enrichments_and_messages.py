"""Add enrichments and messages

Revision ID: e4b0a1b2c3d4
Revises: dda3a8a4a7f1
Create Date: 2025-09-24 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4b0a1b2c3d4'
down_revision: Union[str, None] = 'dda3a8a4a7f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users: add is_admin
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), nullable=True, server_default=sa.false()))

    # products: approvals and enrichment fields
    with op.batch_alter_table('products') as batch_op:
        batch_op.add_column(sa.Column('is_approved', sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column('unit', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('min_order_qty', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('contact_phone', sa.String(length=30), nullable=True))

    # pawah_projects: approvals
    with op.batch_alter_table('pawah_projects') as batch_op:
        batch_op.add_column(sa.Column('is_approved', sa.Boolean(), nullable=True, server_default=sa.false()))

    # messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('context_type', sa.String(length=20), nullable=False),
        sa.Column('context_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Drop server defaults if needed (so future inserts rely on app defaults)
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('is_admin', server_default=None)
    with op.batch_alter_table('products') as batch_op:
        batch_op.alter_column('is_approved', server_default=None)
    with op.batch_alter_table('pawah_projects') as batch_op:
        batch_op.alter_column('is_approved', server_default=None)


def downgrade() -> None:
    op.drop_table('messages')
    with op.batch_alter_table('pawah_projects') as batch_op:
        batch_op.drop_column('is_approved')
    with op.batch_alter_table('products') as batch_op:
        batch_op.drop_column('contact_phone')
        batch_op.drop_column('min_order_qty')
        batch_op.drop_column('unit')
        batch_op.drop_column('is_approved')
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('is_admin')
