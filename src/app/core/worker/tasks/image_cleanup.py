from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ....models.image import Image, ImageStatus
from ...config import settings

logger = structlog.get_logger()

engine = create_async_engine(
    f"{settings.POSTGRES_ASYNC_PREFIX}{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
    f"{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}",
    echo=False,
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_delete=False)


async def cleanup_temporary_images(ctx) -> str:
    """
    Background task to delete temporary images older than 24 hours.
    Runs periodically to clean up unused image uploads.
    """
    try:
        async with AsyncSessionLocal() as db:
            # Calculate cutoff time (24 hours ago)
            cutoff_time = datetime.now(UTC) - timedelta(hours=24)

            # Find temporary images older than 24 hours
            query = select(Image).where(
                and_(
                    Image.status == ImageStatus.TEMPORARY,
                    Image.created_at < cutoff_time,
                    Image.is_deleted == False,  # noqa: E712
                )
            )

            result = await db.execute(query)
            temporary_images = result.scalars().all()

            deleted_count = 0
            failed_count = 0

            for image in temporary_images:
                try:
                    # Delete physical file
                    file_path = Path(settings.BASE_DIR) / "uploads" / "images" / Path(image.file_path).name
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"Deleted image file: {image.file_path}")

                    # Soft delete from database
                    image.is_deleted = True
                    image.deleted_at = datetime.now(UTC)
                    deleted_count += 1

                except Exception as e:
                    logger.error(f"Error deleting image {image.id}: {str(e)}")
                    failed_count += 1

            # Commit all changes
            if deleted_count > 0:
                await db.commit()

            message = f"Cleaned up {deleted_count} temporary images"
            if failed_count > 0:
                message += f" ({failed_count} failed)"

            logger.info(message)
            return message

    except Exception as e:
        logger.error(f"Error in cleanup_temporary_images task: {str(e)}")
        return f"Error: {str(e)}"
