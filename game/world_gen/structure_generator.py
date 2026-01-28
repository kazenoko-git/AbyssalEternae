# game/world_gen/structure_generator.py

import random

class StructureSelector:
    """
    Selects pre-made model files for structures based on style and seed.
    """
    
    STRUCTURE_SETS = {
        "Village": [
            "house_village_small_01",
            "house_village_small_02",
            "house_village_large_01",
            "shop_village_vintage_01",
            "blacksmith_village_01"
        ],
        "City": [
            "house_city_row_01",
            "shop_city_commercial_01",
            "apartment_city_01",
            "office_city_small_01"
        ],
        "Outpost": [
            "tent_outpost_01",
            "shack_outpost_01",
            "tower_watch_01"
        ]
    }
    
    @staticmethod
    def get_structure_model(seed: int, style: str = "Village") -> str:
        """
        Select a model filename based on seed and style.
        """
        rng = random.Random(seed)
        
        # Fallback to Village if style unknown
        model_list = StructureSelector.STRUCTURE_SETS.get(style, StructureSelector.STRUCTURE_SETS["Village"])
        
        # Pick random model
        model_name = rng.choice(model_list)
        
        # Return relative path (AssetLoader will handle full path/extension)
        return f"structures/{style.lower()}/{model_name}"
