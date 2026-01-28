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
from game.systems.world_gen.biome_generator import BiomeGenerator
from game.systems.world_gen.civilization_generator import CivilizationGenerator


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
        
        # Generators
        self.biome_gen = None
        self.civ_gen = None

    def get_or_create_dimension(self, dimension_id: str, seed: int) -> Dict:
        """Retrieve a dimension or generate it if it doesn't exist."""
        
        # Check DB
        dim = self.db.fetch_one("SELECT * FROM dimensions WHERE dimension_id = %s", (dimension_id,))
        if dim:
            self._init_generators(dim['seed'])
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
        
        self._init_generators(seed)
        return self.db.fetch_one("SELECT * FROM dimensions WHERE dimension_id = %s", (dimension_id,))

    def _init_generators(self, seed):
        self.biome_gen = BiomeGenerator(seed)
        self.civ_gen = CivilizationGenerator(seed)

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
        
        # --- Biome Determination ---
        # Sample biome at center of region
        center_x = x * self.region_size + self.region_size/2
        center_y = y * self.region_size + self.region_size/2
        biome_data = self.biome_gen.get_biome_data(center_x, center_y)
        biome = biome_data['biome']
        
        # print(f"Generating Region {region_id}: {biome}") 
        
        # --- Terrain Heightmap Generation ---
        heightmap_data = self._generate_heightmap(dim_seed, x, y)
        
        # --- Civilization & Props ---
        entities = []
        
        # Check for Settlements
        civ_data = self.civ_gen.get_civilization_data(center_x, center_y, biome_data)
        
        if civ_data['is_city'] or civ_data['is_village']:
            # Generate Settlement
            settlement_type = "city" if civ_data['is_city'] else "village"
            buildings = self.civ_gen.generate_settlement_layout(center_x, center_y, settlement_type)
            
            for b in buildings:
                # Clamp to ground
                # We need to construct a temporary region dict to use get_height_at_world_pos
                temp_region_data = {
                    'coordinates_x': x,
                    'coordinates_y': y,
                    'heightmap_data': json.dumps(heightmap_data.tolist())
                }
                cell_size = self.region_size / self.terrain_resolution
                b_z = get_height_at_world_pos(b['x'], b['y'], temp_region_data, cell_size)
                
                if b_z > -1.5:
                    b['z'] = b_z
                    b['scale'] = 1.0
                    entities.append(b)
        else:
            # Generate Nature Props
            num_props = rng.randint(5, 15)
            # Adjust density based on biome
            if "Forest" in biome or "Jungle" in biome: num_props *= 3
            if "Desert" in biome: num_props //= 2
            
            for _ in range(num_props):
                prop_x = x * self.region_size + rng.uniform(-self.region_size/2, self.region_size/2)
                prop_y = y * self.region_size + rng.uniform(-self.region_size/2, self.region_size/2)
                
                temp_region_data = {
                    'coordinates_x': x,
                    'coordinates_y': y,
                    'heightmap_data': json.dumps(heightmap_data.tolist())
                }
                cell_size = self.region_size / self.terrain_resolution
                prop_z = get_height_at_world_pos(prop_x, prop_y, temp_region_data, cell_size)
                
                if prop_z > -1.5:
                    model_type = "tree"
                    if "Desert" in biome or "Volcanic" in biome or "Mountain" in biome:
                        model_type = "rock"
                    elif rng.random() > 0.8:
                        model_type = "rock"
                    
                    prop = {
                        "type": "prop",
                        "model": model_type,
                        "x": prop_x,
                        "y": prop_y,
                        "z": prop_z,
                        "scale": rng.uniform(0.8, 1.5),
                        "seed": rng.randint(0, 10000),
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
        
        rows = self.terrain_resolution + 1
        cols = self.terrain_resolution + 1
        
        heightmap = np.zeros((rows, cols), dtype=np.float32)
        
        world_origin_x = region_x * self.region_size
        world_origin_y = region_y * self.region_size
        
        cell_world_size = self.region_size / self.terrain_resolution
        
        for r in range(rows):
            for c in range(cols):
                wx = world_origin_x + c * cell_world_size
                wy = world_origin_y + r * cell_world_size
                
                # Get Biome Data for this point to modulate height
                biome_data = self.biome_gen.get_biome_data(wx, wy)
                height_mod = self.biome_gen.get_height_modifier(biome_data)
                
                # Generate Composite Height
                height = generate_composite_height(wx, wy, dim_seed) * height_mod
                
                # Add extra noise for "Erosion" if high erosion factor
                if biome_data['erosion'] > 0.5:
                    height += (random.random() - 0.5) * 2.0 # Simple jaggedness

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
