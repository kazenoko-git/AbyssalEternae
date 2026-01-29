# aurora_engine/database/migrations.py

from typing import List, Callable
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.core.logging import get_logger

logger = get_logger()

class Migration:
    """Single database migration."""

    def __init__(self, version: int, description: str,
                 upgrade: Callable, downgrade: Callable):
        self.version = version
        self.description = description
        self.upgrade = upgrade
        self.downgrade = downgrade


class MigrationManager:
    """
    Manages database schema migrations.
    Allows safe schema updates without losing data.
    """

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.migrations: List[Migration] = []
        self._ensure_migration_table()

    def _ensure_migration_table(self):
        """Create migrations tracking table."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at INTEGER NOT NULL
            )
        """)
        self.db.commit()

    def register_migration(self, migration: Migration):
        """Register a migration."""
        self.migrations.append(migration)
        self.migrations.sort(key=lambda m: m.version)

    def get_current_version(self) -> int:
        """Get current schema version."""
        result = self.db.fetch_one(
            "SELECT MAX(version) as version FROM schema_migrations"
        )
        return result['version'] if result and result['version'] else 0

    def migrate_to_latest(self):
        """Apply all pending migrations."""
        current_version = self.get_current_version()

        for migration in self.migrations:
            if migration.version > current_version:
                logger.info(f"Applying migration {migration.version}: {migration.description}")

                try:
                    migration.upgrade(self.db)

                    import time
                    self.db.execute(
                        "INSERT INTO schema_migrations (version, description, applied_at) VALUES (?, ?, ?)",
                        (migration.version, migration.description, int(time.time()))
                    )
                    self.db.commit()

                    logger.info(f"Migration {migration.version} applied successfully")
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Migration {migration.version} failed: {e}")
                    raise

    def rollback(self, target_version: int):
        """Rollback to a specific version."""
        current_version = self.get_current_version()

        for migration in reversed(self.migrations):
            if migration.version > target_version and migration.version <= current_version:
                logger.info(f"Rolling back migration {migration.version}: {migration.description}")

                try:
                    migration.downgrade(self.db)

                    self.db.execute(
                        "DELETE FROM schema_migrations WHERE version = ?",
                        (migration.version,)
                    )
                    self.db.commit()

                    logger.info(f"Migration {migration.version} rolled back")
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Rollback of migration {migration.version} failed: {e}")
                    raise


# Example migration
def create_example_migration():
    """Example: Adding a new column to npcs table."""

    def upgrade(db: DatabaseManager):
        db.execute("ALTER TABLE npcs ADD COLUMN reputation INTEGER DEFAULT 0")

    def downgrade(db: DatabaseManager):
        # SQLite doesn't support DROP COLUMN easily, need to recreate table
        # MySQL supports DROP COLUMN
        db.execute("ALTER TABLE npcs DROP COLUMN reputation")

    return Migration(
        version=2,
        description="Add reputation column to NPCs",
        upgrade=upgrade,
        downgrade=downgrade
    )
