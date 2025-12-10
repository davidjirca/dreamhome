"""Create properties table

Revision ID: 002
Revises: 001
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')

    # Create enums
    property_type = postgresql.ENUM(
        'apartment', 'house', 'studio', 'penthouse',
        'villa', 'duplex', 'land', 'commercial',
        name='propertytype'
    )
    property_type.create(op.get_bind())

    property_status = postgresql.ENUM(
        'draft', 'active', 'sold', 'rented', 'expired',
        name='propertystatus'
    )
    property_status.create(op.get_bind())

    listing_type = postgresql.ENUM(
        'sale', 'rent',
        name='listingtype'
    )
    listing_type.create(op.get_bind())

    # Create properties table
    op.create_table(
        'properties',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('property_type', property_type, nullable=False),
        sa.Column('listing_type', listing_type, nullable=False),
        sa.Column('status', property_status, nullable=False, server_default='draft'),
        sa.Column('price', sa.Numeric(12, 2), nullable=False),
        sa.Column('price_per_sqm', sa.Numeric(10, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='RON'),
        sa.Column('negotiable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('total_area', sa.Numeric(10, 2), nullable=False),
        sa.Column('usable_area', sa.Numeric(10, 2), nullable=True),
        sa.Column('rooms', sa.Integer(), nullable=False),
        sa.Column('bedrooms', sa.Integer(), nullable=False),
        sa.Column('bathrooms', sa.Integer(), nullable=False),
        sa.Column('floor', sa.Integer(), nullable=True),
        sa.Column('total_floors', sa.Integer(), nullable=True),
        sa.Column('year_built', sa.Integer(), nullable=True),
        sa.Column('balconies', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('parking_spots', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('has_garage', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_terrace', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_garden', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_furnished', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('heating_type', sa.String(50), nullable=True),
        sa.Column('energy_rating', sa.String(10), nullable=True),
        sa.Column('address', sa.String(255), nullable=False),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('county', sa.String(100), nullable=False),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('neighborhood', sa.String(100), nullable=True),
        sa.Column('latitude', sa.Numeric(10, 8), nullable=True),
        sa.Column('longitude', sa.Numeric(11, 8), nullable=True),
        sa.Column('location', geoalchemy2.Geography(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('photos', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('main_photo', sa.String(500), nullable=True),
        sa.Column('photo_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('favorite_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_refreshed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    )

    # Create indexes
    op.create_index('ix_properties_id', 'properties', ['id'])
    op.create_index('ix_properties_owner_id', 'properties', ['owner_id'])
    op.create_index('ix_properties_property_type', 'properties', ['property_type'])
    op.create_index('ix_properties_listing_type', 'properties', ['listing_type'])
    op.create_index('ix_properties_status', 'properties', ['status'])
    op.create_index('ix_properties_city', 'properties', ['city'])
    op.create_index('ix_properties_price', 'properties', ['price'])
    op.create_index('ix_properties_rooms', 'properties', ['rooms'])
    op.create_index('ix_properties_slug', 'properties', ['slug'])

    # Create spatial index
    op.execute('CREATE INDEX idx_properties_location ON properties USING GIST(location)')


def downgrade() -> None:
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS idx_properties_location')
    op.drop_index('ix_properties_slug', table_name='properties')
    op.drop_index('ix_properties_rooms', table_name='properties')
    op.drop_index('ix_properties_price', table_name='properties')
    op.drop_index('ix_properties_city', table_name='properties')
    op.drop_index('ix_properties_status', table_name='properties')
    op.drop_index('ix_properties_listing_type', table_name='properties')
    op.drop_index('ix_properties_property_type', table_name='properties')
    op.drop_index('ix_properties_owner_id', table_name='properties')
    op.drop_index('ix_properties_id', table_name='properties')

    # Drop table
    op.drop_table('properties')

    # Drop enums
    postgresql.ENUM(name='listingtype').drop(op.get_bind())
    postgresql.ENUM(name='propertystatus').drop(op.get_bind())
    postgresql.ENUM(name='propertytype').drop(op.get_bind())

    # Drop PostGIS extension (optional - keep it if other tables use it)
    # op.execute('DROP EXTENSION IF EXISTS postgis')