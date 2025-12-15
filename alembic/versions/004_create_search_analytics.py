"""Create search analytics table

Revision ID: 004
Revises: 003
Create Date: 2024-01-25 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create search_queries table for analytics
    op.create_table(
        'search_queries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),

        # Search parameters
        sa.Column('search_text', sa.String(500), nullable=True),
        sa.Column('filters', postgresql.JSON(astext_type=sa.Text()), nullable=False),

        # Results
        sa.Column('result_count', sa.Integer(), nullable=False),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),

        # User interaction
        sa.Column('clicked_property_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('clicked_at', sa.DateTime(timezone=True), nullable=True),

        # Metadata
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('referer', sa.String(500), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['clicked_property_id'], ['properties.id'], ondelete='SET NULL'),
    )

    # Indexes for analytics queries
    op.create_index('ix_search_queries_id', 'search_queries', ['id'])
    op.create_index('ix_search_queries_user_id', 'search_queries', ['user_id'])
    op.create_index('ix_search_queries_created_at', 'search_queries', ['created_at'])
    op.create_index('ix_search_queries_search_text', 'search_queries', ['search_text'])

    # Index for finding popular searches
    op.create_index(
        'ix_search_queries_popular',
        'search_queries',
        ['search_text', 'created_at'],
        postgresql_where="search_text IS NOT NULL"
    )

    # GIN index on filters JSONB for complex queries
    op.create_index(
        'ix_search_queries_filters',
        'search_queries',
        ['filters'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_search_queries_filters', table_name='search_queries')
    op.drop_index('ix_search_queries_popular', table_name='search_queries')
    op.drop_index('ix_search_queries_search_text', table_name='search_queries')
    op.drop_index('ix_search_queries_created_at', table_name='search_queries')
    op.drop_index('ix_search_queries_user_id', table_name='search_queries')
    op.drop_index('ix_search_queries_id', table_name='search_queries')

    # Drop table
    op.drop_table('search_queries')