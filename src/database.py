")
        return False


# Async support (optional)
try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from contextlib import asynccontextmanager

    class AsyncDatabaseManager:
        """Async database manager for high-performance operations."""

        def __init__(self, config: Optional[DatabaseConfig] = None):
            self.config = config or DatabaseConfig()
            self._engine = None
            self._session_factory = None

        async def get_engine(self):
            if self._engine is None:
                self._engine = create_async_engine(
                    self.config.async_database_url,
                    echo=self.config.echo,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow
                )
            return self._engine

        async def get_session_factory(self):
            if self._session_factory is None:
                engine = await self.get_engine()
                self._session_factory = async_sessionmaker(
                    engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )
            return self._session_factory

        @asynccontextmanager
        async def session_scope(self):
            factory = await self.get_session_factory()
            async with factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

    async_db_manager = AsyncDatabaseManager()

except ImportError:
    # Async support not available
    async_db_manager = None
