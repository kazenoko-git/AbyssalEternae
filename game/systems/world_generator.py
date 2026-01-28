# game/systems/world_generator.py

import random
import json
import time
import numpy as np
from typing import Dict, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from aurora_engine.database.db_manager import DatabaseManager
from game.ai.ai_generator import AIContentGenerator
from game.utils.terrain import generate_composite_height, get_height_at_world_pos


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
        self.terrain_resolution = 20 # Higher resolution for better mountains
        self.executor = ThreadPoolExecutor(max_workers=2) # Background generation
        
        # In-memory cache for generated regions to reduce DB hits
        self.known_regions: Dict[str, Dict] = {}

    def get_or_create_dimension(self, dimension_id: str, seed: int) -> Dict:
        """Retrieve a dimension or generate it if it doesn't exist."""
        
        # Check DB
        dim = self.db.fetch_one("SELECT * FROM dimensions WHERE dimension_id = %s", (dimension_id,))
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
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (dimension_id, name, seed, json.dumps(physics), json.dumps(visuals), int(time.time())))
        self.db.commit()
        
        return self.db.fetch_one("SELECT * FROM dimensions WHERE dimension_id = %s", (dimension_id,))

    def generate_region_async(self, dimension_id: str, x: int, y: int):
        """Submit a region generation task to the background thread."""
        return self.executor.submit(self.generate_region, dimension_id, x, y)

    def generate_region(self, dimension_id: str, x: int, y: int) -> Dict:
        """Generate a specific chunk/region within a dimension."""
        region_id = f"{dimension_id}_{x}_{y}"
        
        # Check Memory Cache
        if region_id in self.known_regions:
            return self.known_regions[region_id]
        
        # Check DB
        region = self.db.fetch_one("SELECT * FROM regions WHERE region_id = %s", (region_id,))
        if region:
            region_dict = dict(region)
            self.known_regions[region_id] = region_dict # Cache it
            return region_dict
            
        # Get Dimension Context
        dim = self.get_or_create_dimension(dimension_id, 0) # Seed 0 fallback if not found, but should be found
        dim_seed = dim['seed']
        
        # Region Seed
        region_seed = hash((dim_seed, x, y))
        rng = random.Random(region_seed)
        
        # Biome Selection (Simple logic for now)
        biomes = ["Forest", "Desert", "Tundra", "Volcanic", "Crystal"]
        biome = rng.choice(biomes)
        
        # print(f"Generating Region {region_id}: {biome}") # Avoid print spam in thread
        
        # --- Terrain Heightmap Generation ---
        # REMOVED scale_mod from height generation to ensure seamless terrain
        # Biome only affects props and coloring now
        
        heightmap_data = self._generate_heightmap(dim_seed, x, y)
        
        # Generate Entities (Procedural Placement)
        entities = []
        num_props = rng.randint(5, 15) # Reduced prop count for performance
        for _ in range(num_props):
            prop_x = x * self.region_size + rng.uniform(-self.region_size/2, self.region_size/2)
            prop_y = y * self.region_size + rng.uniform(-self.region_size/2, self.region_size/2)
            
            # Get height at prop position using bilinear interpolation on the generated heightmap
            # We need to construct a temporary region dict to use get_height_at_world_pos
            temp_region_data = {
                'coordinates_x': x,
                'coordinates_y': y,
                'heightmap_data': json.dumps(heightmap_data.tolist())
            }
            cell_size = self.region_size / self.terrain_resolution
            prop_z = get_height_at_world_pos(prop_x, prop_y, temp_region_data, cell_size)
            
            # Only spawn if above water level (e.g., -1.5)
            if prop_z > -1.5:
                # Determine prop type based on biome
                model_type = "tree"
                if biome == "Desert" or biome == "Volcanic":
                    model_type = "rock"
                elif rng.random() > 0.7:
                    model_type = "rock"
                
                prop = {
                    "type": "prop",
                    "model": model_type,
                    "x": prop_x,
                    "y": prop_y,
                    "z": prop_z,
                    "scale": rng.uniform(0.8, 1.5),
                    "seed": rng.randint(0, 10000), # Seed for procedural generation
                    "biome": biome
                }
                entities.append(prop)
            
        # Save Region
        self.db.execute("""
            INSERT INTO regions (region_id, dimension_id, coordinates_x, coordinates_y, biome_type, entities_json, is_generated, heightmap_data)
            VALUES (%s, %s, %s, %s, %s, %s, 1, %s)
        """, (region_id, dimension_id, x, y, biome, json.dumps(entities), json.dumps(heightmap_data.tolist())))
        self.db.commit()
        
        # Fetch and Cache
        new_region = self.db.fetch_one("SELECT * FROM regions WHERE region_id = %s", (region_id,))
        if new_region:
            region_dict = dict(new_region)
            self.known_regions[region_id] = region_dict
            return region_dict
        return None

    def _generate_heightmap(self, dim_seed: int, region_x: int, region_y: int) -> np.ndarray:
        """Generate a heightmap for a specific region."""
        
        # Heightmap grid size (e.g., 10x10 vertices for a 100x100 unit region)
        # Add +1 to rows/cols to share vertices with neighbors
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
                
                # Generate Composite Height (Base + Mountains + Detail)
                # Using world coordinates ensures seamless noise across chunk boundaries
                height = generate_composite_height(wx, wy, dim_seed)
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

    def get_chunks_in_radius(self, player_pos_x: float, player_pos_y: float, radius: int = 1) -> List[Tuple[int, int]]:
        """Calculate chunk coordinates within radius."""
        chunk_x = int(player_pos_x // self.region_size)
        chunk_y = int(player_pos_y // self.region_size)
        
        chunks = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                chunks.append((chunk_x + dx, chunk_y + dy))
        return chunks
