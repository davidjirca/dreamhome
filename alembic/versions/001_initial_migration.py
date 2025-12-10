"""Initial migration - create users table

Revision ID: 001
Revises:
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user role enum
    user_role = postgresql.ENUM('buyer', 'owner', 'agent', 'admin', name='userrole')
    user_role.create(op.get_bind())

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('role', user_role, nullable=False, server_default='buyer', index=True),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('phone_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('license_number', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(),
                  nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Create indexes
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_index('ix_users_id', 'users', ['id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_users_id', table_name='users')
    op.drop_index('ix_users_role', table_name='users')
    op.drop_index('ix_users_email', table_name='users')

    # Drop table
    op.drop_table('users')

    # Drop enum
    user_role = postgresql.ENUM('buyer', 'owner', 'agent', 'admin', name='userrole')
    user_role.drop(op.get_bind())