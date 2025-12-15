"""
Database Seeding Script for imobplan
Generates realistic property data for testing

Usage:
    python scripts/seed_database.py --users 10 --properties 100
    python scripts/seed_database.py --reset  # Clear and reseed
"""

import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.models.property import Property, PropertyType, PropertyStatus, ListingType
from app.core.security import get_password_hash


# Romanian cities with coordinates
ROMANIAN_CITIES = {
    "Bucharest": {
        "county": "Bucharest",
        "lat": 44.4268,
        "lng": 26.1025,
        "neighborhoods": ["Centru Vechi", "Dorobanți", "Pipera", "Berceni", "Drumul Taberei", 
                         "Militari", "Titan", "Pantelimon", "Floreasca", "Aviației"]
    },
    "Cluj-Napoca": {
        "county": "Cluj",
        "lat": 46.7712,
        "lng": 23.6236,
        "neighborhoods": ["Centru", "Mărăști", "Zorilor", "Gheorgheni", "Someșeni",
                         "Iris", "Mănăștur", "Grigorescu", "Bună Ziua", "Dâmbul Rotund"]
    },
    "Timișoara": {
        "county": "Timiș",
        "lat": 45.7489,
        "lng": 21.2087,
        "neighborhoods": ["Centru", "Fabric", "Iosefin", "Elisabetin", "Circumvalațiunii",
                         "Mehala", "Plopi", "Complexul Studențesc", "Dâmbovița", "Ghiroda"]
    },
    "Iași": {
        "county": "Iași",
        "lat": 47.1585,
        "lng": 27.6014,
        "neighborhoods": ["Centru", "Tătărași", "Copou", "Nicolina", "Dacia",
                         "Galata", "Pacurari", "Alexandru cel Bun", "Tudor Vladimirescu", "Cantemir"]
    },
    "Brașov": {
        "county": "Brașov",
        "lat": 45.6579,
        "lng": 25.6012,
        "neighborhoods": ["Centru", "Astra", "Bartolomeu", "Noua", "Tractorul",
                         "Șchei", "Grivița", "Rulmentul", "Darste", "Triaj"]
    },
    "Constanța": {
        "county": "Constanța",
        "lat": 44.1598,
        "lng": 28.6348,
        "neighborhoods": ["Centru", "Mamaia", "Tomis Nord", "Tomis III", "Palazu Mare",
                         "Delfinariu", "Compozitorilor", "Victoria", "Coiciu", "Km 4-5"]
    },
    "Craiova": {
        "county": "Dolj",
        "lat": 44.3302,
        "lng": 23.7949,
        "neighborhoods": ["Centru", "1 Mai", "Romanești", "Craiovița", "Vale Roșie",
                         "Brazda lui Novac", "Electroputere", "Rovine", "Calea Severinului", "Făcăi"]
    },
    "Sibiu": {
        "county": "Sibiu",
        "lat": 45.7983,
        "lng": 24.1256,
        "neighborhoods": ["Centru Istoric", "Vasile Aaron", "Terezian", "Hipodrom", "Tineretului",
                         "Strand", "Turnisor", "Gușterița", "Lazaret", "Valea Aurie"]
    }
}

# Property titles templates
TITLE_TEMPLATES = {
    PropertyType.APARTMENT: [
        "Apartament {} camere, {} mp, {}",
        "Apartament modern {} camere în {}",
        "Apartament spațios {} camere, zona {}",
        "Apartament renovat {} camere, {}",
        "Apartament luminos {} camere în {}"
    ],
    PropertyType.HOUSE: [
        "Casă {} camere, {} mp, {}",
        "Vilă individuală {} camere în {}",
        "Casă familiala {} camere, zona {}",
        "Casă spațioasă {} camere, {}",
        "Casă modernă {} camere în {}"
    ],
    PropertyType.STUDIO: [
        "Garsonieră {} mp, {}",
        "Studio modern {} mp în {}",
        "Garsonieră mobilată {} mp, zona {}",
        "Studio compact {} mp, {}",
        "Garsonieră renovată {} mp în {}"
    ]
}

# Description templates
DESCRIPTIONS = [
    "Proprietate situată într-o zonă liniștită și foarte bine conectată la transportul în comun. "
    "Aproape de școli, grădinițe, magazine și parcuri. Ideal pentru familii sau investiție.",
    
    "Imobil recent renovat cu finisaje de calitate superioară. Orientare excelentă, luminos pe tot parcursul zilei. "
    "Parcare disponibilă în zonă. Acces facil la toate facilitățile urbane.",
    
    "Locuință amplasată într-un cartier în dezvoltare, cu infrastructură modernă. "
    "Apropiere de metrou/stații de autobuz. Zone verzi în proximitate. Ideal pentru tineri profesioniști.",
    
    "Proprietate cu potențial ridicat de investiție, situată în zonă centrală. "
    "Acces rapid la principalele artere de circulație. Magazine, restaurante și instituții în apropiere.",
    
    "Imobil spațios, perfect pentru familii numeroase. Balcon generos cu vedere deschisă. "
    "Compartimentare optimă, multe spații de depozitare. Zonă liniștită și sigură."
]

HEATING_TYPES = [
    "Centrală termică proprie",
    "Centrale termice",
    "Termoficare",
    "Încălzire în pardoseală",
    "Aer condiționat"
]

ENERGY_RATINGS = ["A++", "A+", "A", "B", "C", "D", "E"]

# Unsplash photo collections for different property types
PROPERTY_PHOTOS = {
    PropertyType.APARTMENT: [
        "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800&h=600&fit=crop",  # Modern apartment
        "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&h=600&fit=crop",  # Living room
        "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=800&h=600&fit=crop",  # Kitchen
        "https://images.unsplash.com/photo-1564078516393-cf04bd966897?w=800&h=600&fit=crop",  # Bedroom
        "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=800&h=600&fit=crop",  # Bathroom
        "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=800&h=600&fit=crop",  # Balcony
        "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&h=600&fit=crop",  # Dining
        "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&h=600&fit=crop",  # Interior
    ],
    PropertyType.HOUSE: [
        "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800&h=600&fit=crop",  # House exterior
        "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=800&h=600&fit=crop",  # Modern house
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&h=600&fit=crop",  # Living room
        "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?w=800&h=600&fit=crop",  # Kitchen
        "https://images.unsplash.com/photo-1600121848594-d8644e57abab?w=800&h=600&fit=crop",  # Bedroom
        "https://images.unsplash.com/photo-1598928506311-c55ded91a20c?w=800&h=600&fit=crop",  # Garden
        "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?w=800&h=600&fit=crop",  # Backyard
        "https://images.unsplash.com/photo-1600607687644-c7171b42498b?w=800&h=600&fit=crop",  # Interior
    ],
    PropertyType.STUDIO: [
        "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&h=600&fit=crop",  # Studio apartment
        "https://images.unsplash.com/photo-1536376072261-38c75010e6c9?w=800&h=600&fit=crop",  # Compact living
        "https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?w=800&h=600&fit=crop",  # Small kitchen
        "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=800&h=600&fit=crop",  # Studio interior
        "https://images.unsplash.com/photo-1600566752355-35792bedcfea?w=800&h=600&fit=crop",  # Bathroom
    ],
    PropertyType.PENTHOUSE: [
        "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&h=600&fit=crop",  # Luxury interior
        "https://images.unsplash.com/photo-1600210492493-0946911123ea?w=800&h=600&fit=crop",  # Terrace view
        "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=800&h=600&fit=crop",  # Modern living
        "https://images.unsplash.com/photo-1600573472550-8090b5e0745e?w=800&h=600&fit=crop",  # Kitchen
        "https://images.unsplash.com/photo-1600566752229-250ed79470e6?w=800&h=600&fit=crop",  # Master bedroom
        "https://images.unsplash.com/photo-1600210491892-03d54c0aaf87?w=800&h=600&fit=crop",  # Bathroom luxury
        "https://images.unsplash.com/photo-1600563438938-a9a27216b4f5?w=800&h=600&fit=crop",  # City view
    ],
    PropertyType.VILLA: [
        "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800&h=600&fit=crop",  # Villa exterior
        "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&h=600&fit=crop",  # Pool area
        "https://images.unsplash.com/photo-1600585154363-67eb9e2e2099?w=800&h=600&fit=crop",  # Garden
        "https://images.unsplash.com/photo-1600607687644-aac4c3eac7f4?w=800&h=600&fit=crop",  # Interior
        "https://images.unsplash.com/photo-1600566752355-35792bedcfea?w=800&h=600&fit=crop",  # Living space
        "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=800&h=600&fit=crop",  # Kitchen
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&h=600&fit=crop",  # Bedroom
        "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&h=600&fit=crop",  # Outdoor
    ]
}

# Default photos for other property types
DEFAULT_PROPERTY_PHOTOS = [
    "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1600566752355-35792bedcfea?w=800&h=600&fit=crop",
    "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=800&h=600&fit=crop",
]


def get_property_photos(prop_type: PropertyType, count: int = None) -> tuple[list[str], str]:
    """
    Get realistic photo URLs for a property type
    
    Returns:
        tuple: (list of photo URLs, main photo URL)
    """
    # Get photos for property type
    if prop_type in PROPERTY_PHOTOS:
        available_photos = PROPERTY_PHOTOS[prop_type]
    else:
        available_photos = DEFAULT_PROPERTY_PHOTOS
    
    # Determine number of photos (5-10 random)
    if count is None:
        count = random.randint(5, min(10, len(available_photos)))
    
    # Select random photos
    photos = random.sample(available_photos, min(count, len(available_photos)))
    
    # First photo is the main photo with higher resolution
    main_photo = photos[0].replace("w=800&h=600", "w=1200&h=800")
    
    return photos, main_photo


async def create_users(db: AsyncSession, count: int = 10) -> list[User]:
    """Create test users with different roles"""
    print(f"Creating {count} users...")
    users = []
    
    # Create admin user
    admin = User(
        email="admin@imobplan.ro",
        hashed_password=get_password_hash("Admin123!"),
        role=UserRole.ADMIN,
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_verified=True,
        phone="+40712345678"
    )
    db.add(admin)
    users.append(admin)
    
    # Create agents
    for i in range(count // 3):
        agent = User(
            email=f"agent{i+1}@imobplan.ro",
            hashed_password=get_password_hash("Agent123!"),
            role=UserRole.AGENT,
            first_name=f"Agent{i+1}",
            last_name="Imobiliar",
            is_active=True,
            is_verified=True,
            phone=f"+407{random.randint(10000000, 99999999)}",
            company_name=f"Agenția Imobiliară {['Premium', 'Elite', 'Top', 'Star', 'Pro'][i % 5]}",
            license_number=f"LIC-{random.randint(1000, 9999)}"
        )
        db.add(agent)
        users.append(agent)
    
    # Create owners
    for i in range(count // 3):
        owner = User(
            email=f"owner{i+1}@imobplan.ro",
            hashed_password=get_password_hash("Owner123!"),
            role=UserRole.OWNER,
            first_name=f"Proprietar{i+1}",
            last_name="Particular",
            is_active=True,
            is_verified=random.choice([True, True, False]),
            phone=f"+407{random.randint(10000000, 99999999)}"
        )
        db.add(owner)
        users.append(owner)
    
    # Create buyers
    for i in range(count - len(users)):
        buyer = User(
            email=f"buyer{i+1}@imobplan.ro",
            hashed_password=get_password_hash("Buyer123!"),
            role=UserRole.BUYER,
            first_name=f"Cumpărător{i+1}",
            last_name="Test",
            is_active=True,
            is_verified=random.choice([True, False]),
            phone=f"+407{random.randint(10000000, 99999999)}"
        )
        db.add(buyer)
        users.append(buyer)
    
    await db.flush()
    print(f"✅ Created {len(users)} users")
    return users


def generate_coordinates(base_lat: float, base_lng: float) -> tuple[float, float]:
    """Generate random coordinates near a base location"""
    # Random offset within ~5km
    lat_offset = random.uniform(-0.045, 0.045)
    lng_offset = random.uniform(-0.045, 0.045)
    return (
        round(base_lat + lat_offset, 6),
        round(base_lng + lng_offset, 6)
    )


def generate_property_title(prop_type: PropertyType, rooms: int, area: float, neighborhood: str) -> str:
    """Generate realistic property title"""
    if prop_type in TITLE_TEMPLATES:
        template = random.choice(TITLE_TEMPLATES[prop_type])
        if prop_type == PropertyType.STUDIO:
            return template.format(int(area), neighborhood)
        else:
            return template.format(rooms, int(area), neighborhood)
    return f"{prop_type.value.title()} {rooms} camere, {int(area)} mp, {neighborhood}"


async def create_properties(db: AsyncSession, users: list[User], count: int = 100) -> list[Property]:
    """Create test properties with realistic data"""
    print(f"Creating {count} properties...")
    properties = []
    
    # Filter users who can own properties (agents and owners)
    property_owners = [u for u in users if u.role in [UserRole.AGENT, UserRole.OWNER]]
    
    for i in range(count):
        # Random city
        city_name = random.choice(list(ROMANIAN_CITIES.keys()))
        city_data = ROMANIAN_CITIES[city_name]
        neighborhood = random.choice(city_data["neighborhoods"])
        
        # Generate coordinates
        lat, lng = generate_coordinates(city_data["lat"], city_data["lng"])
        
        # Property type and details
        prop_type = random.choice(list(PropertyType))
        listing_type = random.choice(list(ListingType))
        
        # Get photos for this property type
        photos, main_photo = get_property_photos(prop_type)
        
        # Size and rooms based on property type
        if prop_type == PropertyType.STUDIO:
            rooms = 1
            bedrooms = 0
            total_area = random.randint(25, 45)
        elif prop_type == PropertyType.APARTMENT:
            rooms = random.choice([2, 2, 3, 3, 3, 4, 4])
            bedrooms = rooms - 1
            total_area = rooms * random.randint(20, 35)
        elif prop_type == PropertyType.HOUSE:
            rooms = random.choice([3, 4, 4, 5, 5, 6])
            bedrooms = rooms - 1
            total_area = rooms * random.randint(25, 40)
        else:
            rooms = random.randint(2, 5)
            bedrooms = max(1, rooms - 1)
            total_area = rooms * random.randint(20, 35)
        
        usable_area = total_area * random.uniform(0.85, 0.95)
        bathrooms = 1 if rooms <= 2 else random.randint(1, 2)
        
        # Price calculation (realistic Romanian market prices)
        base_price_per_sqm = {
            "Bucharest": random.randint(1200, 2500),
            "Cluj-Napoca": random.randint(1500, 2800),
            "Timișoara": random.randint(1100, 1800),
            "Iași": random.randint(1000, 1600),
            "Brașov": random.randint(1200, 2000),
            "Constanța": random.randint(900, 1500),
            "Craiova": random.randint(800, 1200),
            "Sibiu": random.randint(1100, 1700)
        }
        
        price_per_sqm = base_price_per_sqm.get(city_name, 1000)
        if listing_type == ListingType.RENT:
            price = total_area * random.randint(4, 8)  # EUR per month
        else:
            price = total_area * price_per_sqm * random.uniform(0.9, 1.1)
        
        # Generate title
        title = generate_property_title(prop_type, rooms, total_area, neighborhood)
        
        # Floor (for apartments)
        floor = None
        total_floors = None
        if prop_type in [PropertyType.APARTMENT, PropertyType.STUDIO, PropertyType.PENTHOUSE]:
            total_floors = random.randint(4, 10)
            floor = random.randint(0, total_floors)
        
        # Features
        has_parking = random.choice([True, False, False])
        parking_spots = random.randint(1, 2) if has_parking else 0
        has_garage = random.choice([True, False]) if prop_type == PropertyType.HOUSE else False
        has_terrace = random.choice([True, False]) if prop_type in [PropertyType.PENTHOUSE, PropertyType.HOUSE] else False
        has_garden = random.choice([True, False]) if prop_type == PropertyType.HOUSE else False
        is_furnished = random.choice([True, True, False, False])
        balconies = random.randint(0, 2) if prop_type != PropertyType.STUDIO else random.choice([0, 1])
        
        # Status
        status_weights = [
            (PropertyStatus.ACTIVE, 0.7),
            (PropertyStatus.DRAFT, 0.15),
            (PropertyStatus.SOLD, 0.08),
            (PropertyStatus.RENTED, 0.05) if listing_type == ListingType.RENT else (PropertyStatus.SOLD, 0.02),
            (PropertyStatus.EXPIRED, 0.05)
        ]
        status = random.choices(
            [s[0] for s in status_weights],
            weights=[s[1] for s in status_weights]
        )[0]
        
        # Timestamps
        created_days_ago = random.randint(1, 90)
        created_at = datetime.utcnow() - timedelta(days=created_days_ago)
        published_at = created_at + timedelta(days=random.randint(0, 3)) if status != PropertyStatus.DRAFT else None
        expires_at = published_at + timedelta(days=60) if published_at else None
        
        # Create property
        prop = Property(
            owner_id=random.choice(property_owners).id,
            title=title,
            description=random.choice(DESCRIPTIONS),
            property_type=prop_type,
            listing_type=listing_type,
            status=status,
            price=Decimal(str(round(price, 2))),
            price_per_sqm=Decimal(str(round(price / total_area, 2))),
            currency="EUR",
            negotiable=random.choice([True, False]),
            total_area=Decimal(str(round(total_area, 2))),
            usable_area=Decimal(str(round(usable_area, 2))),
            rooms=rooms,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            floor=floor,
            total_floors=total_floors,
            year_built=random.randint(1970, 2024) if random.random() > 0.1 else None,
            balconies=balconies,
            parking_spots=parking_spots,
            has_garage=has_garage,
            has_terrace=has_terrace,
            has_garden=has_garden,
            is_furnished=is_furnished,
            heating_type=random.choice(HEATING_TYPES),
            energy_rating=random.choice(ENERGY_RATINGS),
            address=f"Strada {random.choice(['Republicii', 'Libertății', 'Unirii', 'Mihai Viteazu', 'Avram Iancu'])} nr. {random.randint(1, 200)}",
            city=city_name,
            county=city_data["county"],
            postal_code=f"{random.randint(100000, 999999)}",
            neighborhood=neighborhood,
            latitude=Decimal(str(lat)),
            longitude=Decimal(str(lng)),
            location=f"SRID=4326;POINT({lng} {lat})",
            photos=photos,
            main_photo=main_photo,
            photo_count=len(photos),
            slug=f"{title.lower().replace(' ', '-').replace(',', '')}-{i}",
            view_count=random.randint(0, 500) if status == PropertyStatus.ACTIVE else 0,
            favorite_count=random.randint(0, 50) if status == PropertyStatus.ACTIVE else 0,
            created_at=created_at,
            updated_at=created_at + timedelta(days=random.randint(0, 5)),
            published_at=published_at,
            expires_at=expires_at,
            last_refreshed_at=published_at + timedelta(days=random.randint(0, 30)) if published_at else None
        )
        
        db.add(prop)
        properties.append(prop)
        
        if (i + 1) % 20 == 0:
            print(f"  Created {i + 1}/{count} properties...")
    
    await db.flush()
    print(f"✅ Created {len(properties)} properties")
    return properties


async def seed_database(users_count: int = 10, properties_count: int = 100, reset: bool = False):
    """Main seeding function"""
    print("=" * 60)
    print("🌱 Database Seeding Script for imobplan")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        try:
            if reset:
                print("\n⚠️  Clearing existing data...")
                from sqlalchemy import text
                await db.execute(text("DELETE FROM properties"))
                await db.execute(text("DELETE FROM users"))
                await db.commit()
                print("✅ Database cleared")
            
            print(f"\n📊 Creating test data:")
            print(f"  - Users: {users_count}")
            print(f"  - Properties: {properties_count}")
            print()
            
            # Create users
            users = await create_users(db, users_count)
            
            # Create properties
            properties = await create_properties(db, users, properties_count)
            
            # Commit all changes
            await db.commit()
            
            print("\n" + "=" * 60)
            print("✅ Database seeding completed successfully!")
            print("=" * 60)
            print(f"\n📈 Summary:")
            print(f"  - Total users: {len(users)}")
            print(f"  - Total properties: {len(properties)}")
            print(f"  - Active properties: {sum(1 for p in properties if p.status == PropertyStatus.ACTIVE)}")
            print(f"  - Cities covered: {len(ROMANIAN_CITIES)}")
            print()
            print("🔐 Test Credentials:")
            print("  Admin:  admin@imobplan.ro / Admin123!")
            print("  Agent:  agent1@imobplan.ro / Agent123!")
            print("  Owner:  owner1@imobplan.ro / Owner123!")
            print("  Buyer:  buyer1@imobplan.ro / Buyer123!")
            print()
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error during seeding: {e}")
            raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed the database with test data")
    parser.add_argument("--users", type=int, default=10, help="Number of users to create")
    parser.add_argument("--properties", type=int, default=100, help="Number of properties to create")
    parser.add_argument("--reset", action="store_true", help="Clear existing data before seeding")
    
    args = parser.parse_args()
    
    # Run seeding
    asyncio.run(seed_database(
        users_count=args.users,
        properties_count=args.properties,
        reset=args.reset
    ))