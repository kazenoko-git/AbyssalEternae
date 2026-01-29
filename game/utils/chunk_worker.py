# game/utils/chunk_worker.py

import json
import numpy as np
import os
from game.utils.terrain import create_terrain_mesh_from_heightmap
from game.utils.tree_generator import create_procedural_tree_mesh
from game.utils.rock_generator import create_procedural_rock_mesh
from game.world_gen.structure_generator import StructureGenerator

def generate_chunk_meshes(region_data):
    """
    Worker function to generate meshes for a chunk in a background thread.
    Returns a dictionary of { 'terrain': Mesh, 'props': [ (entity_data, Mesh) ] }
    For model-based entities, Mesh will be None, and entity_data will contain 'model_path'.
    """
    result = {
        'terrain': None,
        'props': []
    }
    
    # 1. Terrain Mesh
    if 'heightmap_data' in region_data and region_data['heightmap_data']:
        heightmap = np.array(json.loads(region_data['heightmap_data']), dtype=np.float32)
        cell_size = 100.0 / (heightmap.shape[0]-1)
        result['terrain'] = create_terrain_mesh_from_heightmap(heightmap, cell_size=cell_size)
        
    # 2. Prop Meshes
    entities = json.loads(region_data['entities_json'])
    biome = region_data.get('biome_type', 'Forest')
    
    for entity_data in entities:
        seed = entity_data.get('seed', 0)
        scale = entity_data.get('scale', 1.0)
        mesh = None
        
        if entity_data.get('type') == 'prop':
            if entity_data['model'] == 'rock':
                mesh = create_procedural_rock_mesh(seed, scale=scale)
                
            elif entity_data['model'] == 'tree':
                tree_type = "Oak"
                if "Tundra" in biome: tree_type = "Pine"
                elif "Swamp" in biome: tree_type = "Willow"
                elif "Jungle" in biome: tree_type = "Oak" 
                
                mesh = create_procedural_tree_mesh(seed, height=4.0 * scale, radius=0.5 * scale, tree_type=tree_type)
        
        elif entity_data.get('type') == 'structure':
            # Generate procedural building
            style = entity_data.get('style', 'Village')
            mesh = StructureGenerator.generate_building(seed, style=style)
            
        if mesh:
            result['props'].append((entity_data, mesh))
            
    return result
