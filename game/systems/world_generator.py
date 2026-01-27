# game/systems/world_generator.py

import random
import json
import time
from typing import Dict, Optional
from aurora_engine.database.db_manager import DatabaseManager
from game.ai.ai_generator import AIContentGenerator

class WorldGenerator:
    """
    Procedural World Generation System.
    Handles creation of Dimensions, Regions, and initial population.
    Uses AI for metadata/flavor and deterministic algorithms for layout.
    """

    def __init__(self, db_manager: DatabaseManager, ai_generator: AIContentGenerator):
        self.db = db_manager
        self.ai = ai_generator

    def get_or_create_dimension(self, dimension_id: str, seed: int) -> Dict:
        """Retrieve a dimension or generate it if it doesn't exist."""
        
        # Check DB
        dim = self.db.fetch_one("SELECT * FROM dimensions WHERE dimension_id = ?", (dimension_id,))
        if dim:
            return dict(dim)

        # Generate New Dimension
        print(f"Generating new dimension: {dimension_id} (Seed: {seed})")
        
        # 1. Deterministic Randomness
        rng = random.Random(seed)
        
        # 2. AI Generation for Flavor/Rules
        # We ask AI to define the "vibe" and physics tweaks based on the seed hash
        ai_prompt = f"Generate metadata for a fantasy RPG dimension. Seed: {seed}. ID: {dimension_id}. Return JSON with: name, physics_rules (gravity, atmosphere), visual_style (fog_color, skybox_theme)."
        
        # For now, we mock the AI call to ensure stability, but this would call self.ai.generate_content(...)
        # In a real scenario, we'd cache this prompt.
        
        # Fallback/Mock Data
        name = f"Dimension-{seed % 1000}"
        physics = {"gravity": 9.81 * rng.uniform(0.5, 1.5), "atmosphere": "breathable"}
        visuals = {"fog_color": [rng.random(), rng.random(), rng.random()], "skybox": "nebula"}
        
        # 3. Save to DB
        self.db.execute("""
            INSERT INTO dimensions (dimension_id, name, seed, physics_rules_json, visual_style_json, generated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (dimension_id, name, seed, json.dumps(physics), json.dumps(visuals), int(time.time())))
        self.db.commit()
        
        return self.db.fetch_one("SELECT * FROM dimensions WHERE dimension_id = ?", (dimension_id,))

    def generate_region(self, dimension_id: str, x: int, y: int) -> Dict:
        """Generate a specific chunk/region within a dimension."""
        region_id = f"{dimension_id}_{x}_{y}"
        
        # Check DB
        region = self.db.fetch_one("SELECT * FROM regions WHERE region_id = ?", (region_id,))
        if region:
            return dict(region)
            
        # Get Dimension Context
        dim = self.get_or_create_dimension(dimension_id, 0) # Seed 0 fallback if not found, but should be found
        dim_seed = dim['seed']
        
        # Region Seed
        region_seed = hash((dim_seed, x, y))
        rng = random.Random(region_seed)
        
        # Biome Selection (Simple logic for now)
        biomes = ["Forest", "Desert", "Tundra", "Volcanic", "Crystal"]
        biome = rng.choice(biomes)
        
        print(f"Generating Region {region_id}: {biome}")
        
        # Generate Entities (Procedural Placement)
        entities = []
        num_props = rng.randint(5, 20)
        for _ in range(num_props):
            prop = {
                "type": "prop",
                "model": "rock" if rng.random() > 0.5 else "tree",
                "x": x * 100 + rng.uniform(-50, 50), # World coords
                "y": y * 100 + rng.uniform(-50, 50),
                "z": 0, # Ground clamped later
                "scale": rng.uniform(0.8, 1.5)
            }
            entities.append(prop)
            
        # Save Region
        self.db.execute("""
            INSERT INTO regions (region_id, dimension_id, coordinates_x, coordinates_y, biome_type, entities_json, is_generated)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (region_id, dimension_id, x, y, biome, json.dumps(entities)))
        self.db.commit()
        
        return self.db.fetch_one("SELECT * FROM regions WHERE region_id = ?", (region_id,))

    def load_chunks_around_player(self, dimension_id: str, player_pos_x: float, player_pos_y: float, radius: int = 1):
        """Ensure regions around the player are generated and loaded."""
        chunk_x = int(player_pos_x // 100)
        chunk_y = int(player_pos_y // 100)
        
        loaded_regions = []
        
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                cx, cy = chunk_x + dx, chunk_y + dy
                region = self.generate_region(dimension_id, cx, cy)
                loaded_regions.append(region)
                
        return loaded_regions
