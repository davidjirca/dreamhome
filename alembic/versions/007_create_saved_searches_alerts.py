"""Create saved searches and alert preferences tables

Revision ID: 005
Revises: 004
Create Date: 2024-01-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create alert frequency enum
    alert_frequency = postgresql.ENUM(
        'instant', 'daily', 'weekly',
        name='alertfrequency'
    )
    alert_frequency.create(op.get_bind())

    # Create saved_searches table
    op.create_table(
        'saved_searches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('search_params', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        
        # Alert settings
        sa.Column('alert_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('alert_frequency', alert_frequency, nullable=False, server_default='instant'),
        sa.Column('alert_new_listings', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('alert_price_drops', sa.Boolean(), nullable=False, server_default='true'),
        
        # Metadata
        sa.Column('last_alerted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_saved_searches_id', 'saved_searches', ['id'])
    op.create_index('ix_saved_searches_user_id', 'saved_searches', ['user_id'])
    op.create_index('ix_saved_searches_alert_enabled', 'saved_searches', ['alert_enabled'])

    # Create favorites table
    op.create_table(
        'favorites',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'property_id', name='uq_user_property_favorite')
    )

    # Create indexes
    op.create_index('ix_favorites_id', 'favorites', ['id'])
    op.create_index('ix_favorites_user_id', 'favorites', ['user_id'])
    op.create_index('ix_favorites_property_id', 'favorites', ['property_id'])

    # Create email_logs table for tracking sent emails
    op.create_table(
        'email_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('email_to', sa.String(255), nullable=False),
        sa.Column('email_type', sa.String(50), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Create indexes
    op.create_index('ix_email_logs_id', 'email_logs', ['id'])
    op.create_index('ix_email_logs_user_id', 'email_logs', ['user_id'])
    op.create_index('ix_email_logs_email_type', 'email_logs', ['email_type'])
    op.create_index('ix_email_logs_sent_at', 'email_logs', ['sent_at'])

    # Create property_price_history table for tracking price changes
    op.create_table(
        'property_price_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('old_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('new_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('price_change_percent', sa.Numeric(5, 2), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_property_price_history_id', 'property_price_history', ['id'])
    op.create_index('ix_property_price_history_property_id', 'property_price_history', ['property_id'])
    op.create_index('ix_property_price_history_changed_at', 'property_price_history', ['changed_at'])


def downgrade() -> None:
    # Drop tables
    op.drop_index('ix_property_price_history_changed_at', table_name='property_price_history')
    op.drop_index('ix_property_price_history_property_id', table_name='property_price_history')
    op.drop_index('ix_property_price_history_id', table_name='property_price_history')
    op.drop_table('property_price_history')

    op.drop_index('ix_email_logs_sent_at', table_name='email_logs')
    op.drop_index('ix_email_logs_email_type', table_name='email_logs')
    op.drop_index('ix_email_logs_user_id', table_name='email_logs')
    op.drop_index('ix_email_logs_id', table_name='email_logs')
    op.drop_table('email_logs')

    op.drop_index('ix_favorites_property_id', table_name='favorites')
    op.drop_index('ix_favorites_user_id', table_name='favorites')
    op.drop_index('ix_favorites_id', table_name='favorites')
    op.drop_table('favorites')

    op.drop_index('ix_saved_searches_alert_enabled', table_name='saved_searches')
    op.drop_index('ix_saved_searches_user_id', table_name='saved_searches')
    op.drop_index('ix_saved_searches_id', table_name='saved_searches')
    op.drop_table('saved_searches')

    # Drop enum
    postgresql.ENUM(name='alertfrequency').drop(op.get_bind())