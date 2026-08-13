from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings

# NullPool is required here: each Celery task runs in its own asyncio.run()
# event loop. A shared pool would hand connections created in a previous loop
# to the next loop, which asyncpg rejects with "attached to a different loop"
# / "another operation is in progress" — killing the scheduler so sources
# never get refreshed. Fresh connection per task avoids cross-loop reuse.
engine = create_async_engine(settings.database_url, poolclass=NullPool)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
