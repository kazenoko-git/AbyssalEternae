# game/systems/world_generator.py

import random
import json
import time
import numpy as np
from typing import Dict, Optional
from aurora_engine.database.db_manager import DatabaseManager
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.world.terrain_generator import perlin_noise_2d, get_height_at_world_pos


class WorldGenerator:
    """
    Procedural World Generation System.
    Handles creation of Dimensions, Regions, and initial population.
    Uses AI for metadata/flavor and deterministic algorithms for layout.
    """

    def __init__(self, db_manager: DatabaseManager, ai_generator: AIContentGenerator):
        self.db = db_manager
        self.ai = ai_generator
        self.region_size = 100.0 # World units per region
        self.terrain_resolution = 10 # Vertices per 100 units (10x10 grid for heightmap)

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
        
        # --- Terrain Heightmap Generation ---
        heightmap_data = self._generate_heightmap(dim_seed, x, y)
        
        # Generate Entities (Procedural Placement)
        entities = []
        num_props = rng.randint(5, 20)
        for _ in range(num_props):
            prop_x = x * self.region_size + rng.uniform(-self.region_size/2, self.region_size/2)
            prop_y = y * self.region_size + rng.uniform(-self.region_size/2, self.region_size/2)
            
            # Get height at prop position
            # Need to pass region data to get_height_at_world_pos, but region is not saved yet.
            # So we regenerate height for this specific point.
            prop_z = perlin_noise_2d(prop_x, prop_y, seed=dim_seed, octaves=4, persistence=0.5, lacunarity=2.0, scale=0.01) * 10.0 # Scale height
            
            prop = {
                "type": "prop",
                "model": "rock" if rng.random() > 0.5 else "tree",
                "x": prop_x,
                "y": prop_y,
                "z": prop_z,
                "scale": rng.uniform(0.8, 1.5)
            }
            entities.append(prop)
            
        # Save Region
        self.db.execute("""
            INSERT INTO regions (region_id, dimension_id, coordinates_x, coordinates_y, biome_type, entities_json, is_generated, heightmap_data)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (region_id, dimension_id, x, y, biome, json.dumps(entities), json.dumps(heightmap_data.tolist())))
        self.db.commit()
        
        return self.db.fetch_one("SELECT * FROM regions WHERE region_id = ?", (region_id,))

    def _generate_heightmap(self, dim_seed: int, region_x: int, region_y: int) -> np.ndarray:
        """Generate a heightmap for a specific region."""
        
        # Heightmap grid size (e.g., 10x10 vertices for a 100x100 unit region)
        rows = self.terrain_resolution + 1
        cols = self.terrain_resolution + 1
        
        heightmap = np.zeros((rows, cols), dtype=np.float32)
        
        # Calculate world coordinates for each vertex in the heightmap
        # Region origin (bottom-left corner)
        world_origin_x = region_x * self.region_size
        world_origin_y = region_y * self.region_size
        
        cell_world_size = self.region_size / self.terrain_resolution
        
        for r in range(rows):
            for c in range(cols):
                # World position of this vertex
                wx = world_origin_x + c * cell_world_size
                wy = world_origin_y + r * cell_world_size
                
                # Generate Perlin noise for height
                # Scale the noise input coordinates to get desired terrain features
                height = perlin_noise_2d(wx, wy, seed=dim_seed, octaves=4, persistence=0.5, lacunarity=2.0, scale=0.01) * 10.0 # Scale height
                heightmap[r, c] = height
                
        return heightmap

    def load_chunks_around_player(self, dimension_id: str, player_pos_x: float, player_pos_y: float, radius: int = 1):
        """Ensure regions around the player are generated and loaded."""
        chunk_x = int(player_pos_x // self.region_size)
        chunk_y = int(player_pos_y // self.region_size)
        
        loaded_regions = []
        
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                cx, cy = chunk_x + dx, chunk_y + dy
                region = self.generate_region(dimension_id, cx, cy)
                loaded_regions.append(region)
                
        return loaded_regions
