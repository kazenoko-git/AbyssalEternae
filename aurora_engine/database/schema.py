# aurora_engine/database/schema.py

class DatabaseSchema:
    """
    Database schema definitions.
    Defines tables for world state, NPCs, dialogue, etc.
    """

    @staticmethod
    def create_tables(db_manager):
        """Create all database tables."""

        # World state
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS world_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )
        """)

        # NPC profiles
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS npcs (
                npc_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                personality TEXT,
                background TEXT,
                created_at INTEGER NOT NULL
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
                context TEXT,
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
                metadata TEXT,
                created_at INTEGER NOT NULL,
                UNIQUE(content_type, prompt_hash)
            )
        """)

        # Quest data
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                quest_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                objectives TEXT,
                rewards TEXT,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        # Indexes for performance
        db_manager.execute("CREATE INDEX IF NOT EXISTS idx_npc_memory_npc ON npc_memory(npc_id)")
        db_manager.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_npc ON dialogue_history(npc_id)")
        db_manager.execute("CREATE INDEX IF NOT EXISTS idx_ai_cache_lookup ON ai_cache(content_type, prompt_hash)")

        db_manager.commit()