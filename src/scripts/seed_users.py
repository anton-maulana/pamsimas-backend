import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.db.database import AsyncSession, local_session
from app.core.security import get_password_hash
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEED_USERS = [
    {
        "name": "Super Admin",
        "username": "superadmin",
        "email": "superadmin@example.com",
        "password": "Str1ngst!",
        "is_superuser": True,
    },
    {
        "name": "John Doe",
        "username": "johndoe",
        "email": "john@example.com",
        "password": "Password123!",
        "is_superuser": False,
    },
    {
        "name": "Jane Doe",
        "username": "janedoe",
        "email": "jane@example.com",
        "password": "Password123!",
        "is_superuser": False,
    },
]


async def seed_users(session: AsyncSession) -> None:
    for user_data in SEED_USERS:
        query = select(User).filter_by(email=user_data["email"])
        result = await session.execute(query)
        existing = result.scalar_one_or_none()

        if existing is None:
            user = User(
                name=user_data["name"],
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                is_superuser=user_data["is_superuser"],
            )
            session.add(user)
            await session.commit()
            logger.info(f"Created user: {user_data['username']} ({user_data['email']})")
        else:
            logger.info(f"User already exists: {user_data['username']} ({user_data['email']})")


async def main() -> None:
    async with local_session() as session:
        await seed_users(session)


if __name__ == "__main__":
    asyncio.run(main())
