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
        # MySQL: key is reserved word, use backticks or rename. Let's rename to setting_key
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS world_state (
                setting_key VARCHAR(255) PRIMARY KEY,
                value TEXT NOT NULL,
                timestamp BIGINT NOT NULL
            )
        """)

        # Player Saves
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS player_saves (
                save_id INT AUTO_INCREMENT PRIMARY KEY,
                player_name VARCHAR(255) NOT NULL,
                level INT DEFAULT 1,
                experience INT DEFAULT 0,
                current_dimension VARCHAR(255) NOT NULL,
                position_x FLOAT,
                position_y FLOAT,
                position_z FLOAT,
                inventory_json TEXT,
                stats_json TEXT,
                last_played BIGINT NOT NULL
            )
        """)

        # Dimensions (Procedural Metadata)
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS dimensions (
                dimension_id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                seed BIGINT NOT NULL,
                physics_rules_json TEXT, 
                visual_style_json TEXT, 
                difficulty_multiplier FLOAT DEFAULT 1.0,
                generated_at BIGINT NOT NULL
            )
        """)

        # Regions (Chunks/Areas within Dimensions)
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS regions (
                region_id VARCHAR(255) PRIMARY KEY, 
                dimension_id VARCHAR(255) NOT NULL,
                coordinates_x INT NOT NULL,
                coordinates_y INT NOT NULL,
                biome_type VARCHAR(255),
                entities_json LONGTEXT, 
                heightmap_data LONGTEXT, 
                is_generated BOOLEAN DEFAULT 0,
                FOREIGN KEY (dimension_id) REFERENCES dimensions(dimension_id)
            )
        """)

        # NPC profiles
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS npcs (
                npc_id VARCHAR(255) PRIMARY KEY,
                region_id VARCHAR(255),
                name VARCHAR(255) NOT NULL,
                role VARCHAR(255), 
                personality_json TEXT,
                appearance_json TEXT, 
                voice_profile_json TEXT, 
                created_at BIGINT NOT NULL,
                FOREIGN KEY (region_id) REFERENCES regions(region_id)
            )
        """)

        # NPC memory (for AI context)
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS npc_memory (
                memory_id INT AUTO_INCREMENT PRIMARY KEY,
                npc_id VARCHAR(255) NOT NULL,
                event_type VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                emotional_impact FLOAT,
                timestamp BIGINT NOT NULL,
                FOREIGN KEY (npc_id) REFERENCES npcs(npc_id)
            )
        """)

        # Dialogue history
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS dialogue_history (
                dialogue_id INT AUTO_INCREMENT PRIMARY KEY,
                npc_id VARCHAR(255) NOT NULL,
                player_line TEXT,
                npc_line TEXT NOT NULL,
                context_json TEXT,
                timestamp BIGINT NOT NULL,
                FOREIGN KEY (npc_id) REFERENCES npcs(npc_id)
            )
        """)

        # AI-generated content cache
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS ai_cache (
                cache_id INT AUTO_INCREMENT PRIMARY KEY,
                content_type VARCHAR(255) NOT NULL, 
                prompt_hash VARCHAR(255) NOT NULL,
                generated_content LONGTEXT NOT NULL,
                metadata_json TEXT,
                created_at BIGINT NOT NULL,
                UNIQUE(content_type, prompt_hash)
            )
        """)

        # Quest data
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                quest_id VARCHAR(255) PRIMARY KEY,
                npc_id_giver VARCHAR(255),
                title VARCHAR(255) NOT NULL,
                description TEXT,
                objectives_json TEXT,
                rewards_json TEXT,
                status VARCHAR(50) NOT NULL, 
                created_at BIGINT NOT NULL,
                FOREIGN KEY (npc_id_giver) REFERENCES npcs(npc_id)
            )
        """)

        # Boss Registry
        db_manager.execute("""
            CREATE TABLE IF NOT EXISTS bosses (
                boss_id VARCHAR(255) PRIMARY KEY,
                dimension_id VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                archetype VARCHAR(255), 
                abilities_json TEXT, 
                phases_json TEXT, 
                defeated BOOLEAN DEFAULT 0,
                FOREIGN KEY (dimension_id) REFERENCES dimensions(dimension_id)
            )
        """)

        # Indexes (MySQL syntax is slightly different for IF NOT EXISTS on index, usually handled by CREATE INDEX directly or checking schema)
        # Simple CREATE INDEX is fine if it doesn't exist, but MySQL throws error if exists.
        # We can use a try-except block in db_manager or just ignore errors for now in this script.
        # Or use: CREATE INDEX index_name ON table(col)
        # MySQL 8.0+ supports IF NOT EXISTS? No.
        # We will wrap these in try-except in the execution logic or just let them fail if they exist.
        
        try:
            db_manager.execute("CREATE INDEX idx_npc_memory_npc ON npc_memory(npc_id)")
        except: pass
        
        try:
            db_manager.execute("CREATE INDEX idx_dialogue_npc ON dialogue_history(npc_id)")
        except: pass
        
        try:
            db_manager.execute("CREATE INDEX idx_ai_cache_lookup ON ai_cache(content_type, prompt_hash)")
        except: pass
        
        try:
            db_manager.execute("CREATE INDEX idx_regions_lookup ON regions(dimension_id, coordinates_x, coordinates_y)")
        except: pass

        db_manager.commit()
