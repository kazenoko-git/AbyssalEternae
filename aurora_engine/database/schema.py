# aurora_engine/database/schema.py

class DatabaseSchema:
    """
    Database schema definitions.
    Defines tables for world state, NPCs, dialogue, etc.
    """

    @staticmethod
    def create_tables(db_manager):
        """Create all database tables."""

        # World state (Global metadata)
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS world_state (
                key TEXT PRIMARY KEY,
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
                physics_rules_json TEXT, -- Gravity, atmosphere, etc.
                visual_style_json TEXT, -- Fog color, skybox, etc.
                difficulty_multiplier REAL DEFAULT 1.0,
                generated_at INTEGER NOT NULL
            )
        """)

        # Regions (Chunks/Areas within Dimensions)
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS regions (
                region_id TEXT PRIMARY KEY, -- dim_id + coords
                dimension_id TEXT NOT NULL,
                coordinates_x INTEGER NOT NULL,
                coordinates_y INTEGER NOT NULL,
                biome_type TEXT,
                entities_json TEXT, -- Serialized static entities
                heightmap_data TEXT, -- Serialized heightmap array
                is_generated BOOLEAN DEFAULT 0,
                FOREIGN KEY (dimension_id) REFERENCES dimensions(dimension_id)
            )
        """)

        # NPC profiles
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS npcs (
                npc_id TEXT PRIMARY KEY,
                region_id TEXT,
                name TEXT NOT NULL,
                role TEXT, -- Merchant, QuestGiver, etc.
                personality_json TEXT,
                appearance_json TEXT, -- Clothing, body type
                voice_profile_json TEXT, -- TTS settings
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
                content_type TEXT NOT NULL, -- 'dialogue', 'quest', 'lore', 'texture'
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
                status TEXT NOT NULL, -- 'active', 'completed', 'failed'
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
                archetype TEXT, -- 'Dragon', 'Construct', etc.
                abilities_json TEXT, -- AI generated ability set
                phases_json TEXT, -- Phase transition logic
                defeated BOOLEAN DEFAULT 0,
                FOREIGN KEY (dimension_id) REFERENCES dimensions(dimension_id)
            )
        """)

        # Indexes for performance
        db_manager.execute("CREATE INDEX IF NOT EXISTS idx_npc_memory_npc ON npc_memory(npc_id)")
        db_manager.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_npc ON dialogue_history(npc_id)")
        db_manager.execute("CREATE INDEX IF NOT EXISTS idx_ai_cache_lookup ON ai_cache(content_type, prompt_hash)")
        db_manager.execute("CREATE INDEX IF NOT EXISTS idx_regions_lookup ON regions(dimension_id, coordinates_x, coordinates_y)")

        db_manager.commit()
