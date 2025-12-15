"""Add full-text search and optimized indexes

Revision ID: 003
Revises: 002
Create Date: 2024-01-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add full-text search vector column (auto-generated)
    op.execute("""
               ALTER TABLE properties
                   ADD COLUMN search_vector tsvector
                       GENERATED ALWAYS AS (
                           setweight(to_tsvector('romanian', coalesce(title, '')), 'A') ||
                           setweight(to_tsvector('romanian', coalesce(description, '')), 'B') ||
                           setweight(to_tsvector('romanian', coalesce(neighborhood, '')), 'C') ||
                           setweight(to_tsvector('simple', coalesce(city, '')), 'D')
                           ) STORED;
               """)

    # Create GIN index for full-text search
    op.create_index(
        'idx_properties_search_vector',
        'properties',
        ['search_vector'],
        postgresql_using='gin'
    )

    # Composite index for common filter combinations
    op.create_index(
        'idx_properties_search_filters',
        'properties',
        ['city', 'property_type', 'listing_type', 'status', 'price']
    )

    # Partial index for active listings only
    op.execute("""
               CREATE INDEX idx_properties_active_published
                   ON properties (status, published_at DESC, expires_at) WHERE status = 'active' AND deleted_at IS NULL;
               """)

    # Index for room-based searches
    op.create_index(
        'idx_properties_rooms_area',
        'properties',
        ['rooms', 'bedrooms', 'total_area']
    )

    # Index for price range searches
    op.create_index(
        'idx_properties_price_area_type',
        'properties',
        ['price', 'total_area', 'property_type']
    )

    # Index for recent listings
    op.create_index(
        'idx_properties_published_desc',
        'properties',
        [sa.text('published_at DESC')],
        postgresql_where="published_at IS NOT NULL AND deleted_at IS NULL"
    )

    # Add days_online computed field helper (for analytics)
    # This will be calculated in application, but adding index support
    op.create_index(
        'idx_properties_published_created',
        'properties',
        ['published_at', 'created_at']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_properties_published_created', table_name='properties')
    op.execute('DROP INDEX IF EXISTS idx_properties_published_desc')
    op.drop_index('idx_properties_price_area_type', table_name='properties')
    op.drop_index('idx_properties_rooms_area', table_name='properties')
    op.execute('DROP INDEX IF EXISTS idx_properties_active_published')
    op.drop_index('idx_properties_search_filters', table_name='properties')
    op.drop_index('idx_properties_search_vector', table_name='properties')

    # Drop search_vector column
    op.execute('ALTER TABLE properties DROP COLUMN IF EXISTS search_vector')