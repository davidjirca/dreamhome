"""Fix coordinate types from Integer to Numeric

Revision ID: 006
Revises: 005
Create Date: 2026-01-08 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Fix coordinate storage - convert from Integer to Numeric(10, 8) for proper decimal storage
    This is CRITICAL for geospatial queries to work correctly
    """

    # Change latitude from Integer to Numeric(10, 8)
    # Example: 44.42681234 (10 total digits, 8 after decimal)
    op.alter_column(
        'properties',
        'latitude',
        type_=sa.Numeric(10, 8),
        existing_type=sa.Integer(),
        existing_nullable=True
    )

    # Change longitude from Integer to Numeric(11, 8)
    # Example: 26.10250000 (11 total digits, 8 after decimal)
    op.alter_column(
        'properties',
        'longitude',
        type_=sa.Numeric(11, 8),
        existing_type=sa.Integer(),
        existing_nullable=True
    )

    print("✅ Coordinate types fixed: Integer → Numeric(10, 8) and Numeric(11, 8)")
    print("   Coordinates will now store properly: 44.4268 instead of 44")


def downgrade() -> None:
    """Revert coordinate types back to Integer (NOT RECOMMENDED)"""

    op.alter_column(
        'properties',
        'latitude',
        type_=sa.Integer(),
        existing_type=sa.Numeric(10, 8),
        existing_nullable=True
    )

    op.alter_column(
        'properties',
        'longitude',
        type_=sa.Integer(),
        existing_type=sa.Numeric(11, 8),
        existing_nullable=True
    )