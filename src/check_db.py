
import asyncio
from sqlalchemy import text
from app.core.db.database import async_engine

async def check_columns():
    async with async_engine.connect() as conn:
        print("Checking customer table columns:")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'customer';
        """))
        for row in result:
            print(f"Column: {row[0]}, Type: {row[1]}")
            
        print("\nChecking bill table columns:")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'bill';
        """))
        for row in result:
            print(f"Column: {row[0]}, Type: {row[1]}")

if __name__ == "__main__":
    asyncio.run(check_columns())
