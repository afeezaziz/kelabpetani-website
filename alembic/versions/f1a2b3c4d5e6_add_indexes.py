"""Add indexes for performance

Revision ID: f1a2b3c4d5e6
Revises: e4b0a1b2c3d4
Create Date: 2025-09-24 13:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e4b0a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Orders indexes
    op.create_index('ix_orders_buyer_id', 'orders', ['buyer_id'])
    op.create_index('ix_orders_product_id', 'orders', ['product_id'])

    # Messages composite index for contextual fetch
    op.create_index('ix_messages_context', 'messages', ['context_type', 'context_id'])

    # Products composite index for marketplace listing and moderation
    op.create_index(
        'ix_products_active_approved_created',
        'products',
        ['is_active', 'is_approved', 'created_at']
    )

    # Pawah projects composite index for listing and moderation
    op.create_index(
        'ix_pawah_projects_approved_created',
        'pawah_projects',
        ['is_approved', 'created_at']
    )


def downgrade() -> None:
    op.drop_index('ix_pawah_projects_approved_created', table_name='pawah_projects')
    op.drop_index('ix_products_active_approved_created', table_name='products')
    op.drop_index('ix_messages_context', table_name='messages')
    op.drop_index('ix_orders_product_id', table_name='orders')
    op.drop_index('ix_orders_buyer_id', table_name='orders')
