import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPass123",
            "password_confirm": "TestPass123",
            "role": "buyer",
            "first_name": "Test",
            "last_name": "User"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "buyer"
    assert data["first_name"] == "Test"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration with duplicate email"""
    # Register first user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "TestPass123",
            "password_confirm": "TestPass123",
            "role": "buyer"
        }
    )

    # Try to register with same email
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "TestPass123",
            "password_confirm": "TestPass123",
            "role": "buyer"
        }
    )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Test registration with weak password"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "password": "weak",
            "password_confirm": "weak",
            "role": "buyer"
        }
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login"""
    # Register user first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "TestPass123",
            "password_confirm": "TestPass123",
            "role": "buyer"
        }
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "TestPass123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with wrong password"""
    # Register user first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "TestPass123",
            "password_confirm": "TestPass123",
            "role": "buyer"
        }
    )

    # Login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "WrongPass123"
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with nonexistent user"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "TestPass123"
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    """Test getting current user profile"""
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "current@example.com",
            "password": "TestPass123",
            "password_confirm": "TestPass123",
            "role": "buyer",
            "first_name": "Current",
            "last_name": "User"
        }
    )

    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "current@example.com",
            "password": "TestPass123"
        }
    )

    token = login_response.json()["access_token"]

    # Get current user
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "current@example.com"
    assert data["first_name"] == "Current"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test getting current user without authentication"""
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 403  # No authorization header