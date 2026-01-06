"""Create favorites, saved searches, and alert tables

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
    # Create notification frequency enum
    notification_frequency = postgresql.ENUM(
        'immediate', 'daily', 'weekly', 'disabled',
        name='notificationfrequency'
    )
    notification_frequency.create(op.get_bind())
    
    # ============================================================================
    # SAVED SEARCHES TABLE
    # ============================================================================
    op.create_table(
        'saved_searches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # Search details
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Search parameters (JSON)
        sa.Column('filters', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        
        # Notification settings
        sa.Column('email_notifications', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notification_frequency', sa.String(20), nullable=False, server_default='daily'),
        sa.Column('last_notified_at', sa.DateTime(timezone=True), nullable=True),
        
        # Metadata
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('result_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Indexes for saved_searches
    op.create_index('ix_saved_searches_id', 'saved_searches', ['id'])
    op.create_index('ix_saved_searches_user_id', 'saved_searches', ['user_id'])
    op.create_index('ix_saved_searches_is_active', 'saved_searches', ['is_active'])
    
    # Partial index for notification processing
    op.execute("""
        CREATE INDEX ix_saved_searches_notifications 
        ON saved_searches (email_notifications, notification_frequency, last_notified_at)
        WHERE email_notifications = true AND is_active = true
    """)
    
    # GIN index on filters JSONB for complex queries
    op.create_index(
        'ix_saved_searches_filters',
        'saved_searches',
        ['filters'],
        postgresql_using='gin'
    )

    # ============================================================================
    # FAVORITES TABLE
    # ============================================================================
    op.create_table(
        'favorites',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'property_id', name='uq_user_property_favorite'),
    )

    # Indexes for favorites
    op.create_index('ix_favorites_id', 'favorites', ['id'])
    op.create_index('ix_favorites_user_id', 'favorites', ['user_id'])
    op.create_index('ix_favorites_property_id', 'favorites', ['property_id'])
    op.create_index('ix_favorites_created_at', 'favorites', ['created_at'], postgresql_ops={'created_at': 'DESC'})

    # ============================================================================
    # EMAIL LOGS TABLE (for tracking sent emails)
    # ============================================================================
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

    # Indexes for email_logs
    op.create_index('ix_email_logs_id', 'email_logs', ['id'])
    op.create_index('ix_email_logs_user_id', 'email_logs', ['user_id'])
    op.create_index('ix_email_logs_email_type', 'email_logs', ['email_type'])
    op.create_index('ix_email_logs_sent_at', 'email_logs', ['sent_at'])

    # ============================================================================
    # PROPERTY PRICE HISTORY TABLE (for tracking price changes)
    # ============================================================================
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

    # Indexes for property_price_history
    op.create_index('ix_property_price_history_id', 'property_price_history', ['id'])
    op.create_index('ix_property_price_history_property_id', 'property_price_history', ['property_id'])
    op.create_index('ix_property_price_history_changed_at', 'property_price_history', ['changed_at'])


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    
    # Drop property_price_history
    op.drop_index('ix_property_price_history_changed_at', table_name='property_price_history')
    op.drop_index('ix_property_price_history_property_id', table_name='property_price_history')
    op.drop_index('ix_property_price_history_id', table_name='property_price_history')
    op.drop_table('property_price_history')

    # Drop email_logs
    op.drop_index('ix_email_logs_sent_at', table_name='email_logs')
    op.drop_index('ix_email_logs_email_type', table_name='email_logs')
    op.drop_index('ix_email_logs_user_id', table_name='email_logs')
    op.drop_index('ix_email_logs_id', table_name='email_logs')
    op.drop_table('email_logs')

    # Drop favorites
    op.drop_index('ix_favorites_created_at', table_name='favorites')
    op.drop_index('ix_favorites_property_id', table_name='favorites')
    op.drop_index('ix_favorites_user_id', table_name='favorites')
    op.drop_index('ix_favorites_id', table_name='favorites')
    op.drop_table('favorites')

    # Drop saved_searches
    op.drop_index('ix_saved_searches_filters', table_name='saved_searches')
    op.execute('DROP INDEX IF EXISTS ix_saved_searches_notifications')
    op.drop_index('ix_saved_searches_is_active', table_name='saved_searches')
    op.drop_index('ix_saved_searches_user_id', table_name='saved_searches')
    op.drop_index('ix_saved_searches_id', table_name='saved_searches')
    op.drop_table('saved_searches')

    # Drop enum
    postgresql.ENUM(name='notificationfrequency').drop(op.get_bind())