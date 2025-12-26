"""Create saved searches table

Revision ID: 006
Revises: 005
Create Date: 2024-01-26 11:00:00.000000

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
    # Create saved_searches table
    op.create_table(
        'saved_searches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        
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

    # Create indexes
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


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_saved_searches_filters', table_name='saved_searches')
    op.execute('DROP INDEX IF EXISTS ix_saved_searches_notifications')
    op.drop_index('ix_saved_searches_is_active', table_name='saved_searches')
    op.drop_index('ix_saved_searches_user_id', table_name='saved_searches')
    op.drop_index('ix_saved_searches_id', table_name='saved_searches')
    
    # Drop table
    op.drop_table('saved_searches')