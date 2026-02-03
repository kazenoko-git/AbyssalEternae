# aurora_engine/database/schema.py

from aurora_engine.core.logging import get_logger

logger = get_logger()

class DatabaseSchema:
    """
    Database schema definitions.
    Defines tables for world state, NPCs, dialogue, etc.
    """

    @staticmethod
    def drop_tables(db_manager):
        """Drop all tables to reset the database."""
        tables = [
            "world_state", "player_saves", "regions", "npcs", "npc_memory", 
            "dialogue_history", "ai_cache", "quests", "bosses", "dimensions"
        ]
        try:
            # Disable foreign key checks to avoid ordering issues
            db_manager.execute("PRAGMA foreign_keys = OFF")
            for table in tables:
                db_manager.execute(f"DROP TABLE IF EXISTS {table}")
            db_manager.execute("PRAGMA foreign_keys = ON")
            db_manager.commit()
            logger.info("Dropped all database tables")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")

    @staticmethod
    def create_tables(db_manager):
        """Create all database tables."""
        try:
            # World state (Global metadata)
            db_manager.execute("""
                CREATE TABLE IF NOT EXISTS world_state (
                    setting_key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    timestamp INTEGER NOT NULL
                )
            """)

            # Player Saves
            db_manager.execute("""
                CREATE TABLE IF NOT EXISTS player_saves (
                    save_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    experience INTEGER DEFAULT 0,
                    current_dimension TEXT NOT NULL,
                    position_x REAL,
                    position_y REAL,
                    position_z REAL,
                    inventory_json TEXT,
                    stats_json TEXT,
                    last_played INTEGER NOT NULL
                )
            """)

            # Dimensions (Procedural Metadata)
            db_manager.execute("""
                CREATE TABLE IF NOT EXISTS dimensions (
                    dimension_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    seed INTEGER NOT NULL,
                    physics_rules_json TEXT, 
                    visual_style_json TEXT, 
                    difficulty_multiplier REAL DEFAULT 1.0,
                    generated_at INTEGER NOT NULL
                )
            """)

            # Regions (Chunks/Areas within Dimensions)
            db_manager.execute("""
                CREATE TABLE IF NOT EXISTS regions (
                    region_id TEXT PRIMARY KEY, 
                    dimension_id TEXT NOT NULL,
                    coordinates_x INTEGER NOT NULL,
                    coordinates_y INTEGER NOT NULL,
                    biome_type TEXT,
                    entities_json TEXT, 
                    heightmap_data TEXT, 
                    is_generated INTEGER DEFAULT 0,
                    FOREIGN KEY (dimension_id) REFERENCES dimensions(dimension_id)
                )
            """)

            # NPC profiles
            db_manager.execute("""
                CREATE TABLE IF NOT EXISTS npcs (
                    npc_id TEXT PRIMARY KEY,
                    region_id TEXT,
                    name TEXT NOT NULL,
                    role TEXT, 
                    personality_json TEXT,
                    appearance_json TEXT, 
                    voice_profile_json TEXT, 
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (region_id) REFERENCES regions(region_id)
                )
            """)

            # NPC memory (for AI context)
            db_manager.execute("""
                CREATE TABLE IF NOT EXISTS npc_memory (
                    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    npc_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    emotional_impact REAL,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (npc_id) REFERENCES npcs(npc_id)
                )
            """)

            # Dialogue history
            db_manager.execute("""
                CREATE TABLE IF NOT EXISTS dialogue_history (
                    dialogue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    npc_id TEXT NOT NULL,
                    player_line TEXT,
                    npc_line TEXT NOT NULL,
                    context_json TEXT,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (npc_id) REFERENCES npcs(npc_id)
                )
            """)

            # AI-generated content cache
            db_manager.execute("""
                CREATE TABLE IF NOT EXISTS ai_cache (
                    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_type TEXT NOT NULL, 
                    prompt_hash TEXT NOT NULL,
                    generated_content TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at INTEGER NOT NULL,
                    UNIQUE(content_type, prompt_hash)
                )
            """)

            # Quest data
            db_manager.execute("""
                CREATE TABLE IF NOT EXISTS quests (
                    quest_id TEXT PRIMARY KEY,
                    npc_id_giver TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    objectives_json TEXT,
                    rewards_json TEXT,
                    status TEXT NOT NULL, 
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (npc_id_giver) REFERENCES npcs(npc_id)
                )
            """)

            # Boss Registry
            db_manager.execute("""
                CREATE TABLE IF NOT EXISTS bosses (
                    boss_id TEXT PRIMARY KEY,
                    dimension_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    archetype TEXT, 
                    abilities_json TEXT, 
                    phases_json TEXT, 
                    defeated INTEGER DEFAULT 0,
                    FOREIGN KEY (dimension_id) REFERENCES dimensions(dimension_id)
                )
            """)

            # Indexes
            # SQLite supports IF NOT EXISTS for indexes
            db_manager.execute("CREATE INDEX IF NOT EXISTS idx_npc_memory_npc ON npc_memory(npc_id)")
            db_manager.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_npc ON dialogue_history(npc_id)")
            db_manager.execute("CREATE INDEX IF NOT EXISTS idx_ai_cache_lookup ON ai_cache(content_type, prompt_hash)")
            db_manager.execute("CREATE INDEX IF NOT EXISTS idx_regions_lookup ON regions(dimension_id, coordinates_x, coordinates_y)")

            db_manager.commit()
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
