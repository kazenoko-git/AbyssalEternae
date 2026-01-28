# game/examples/debug_memory_stress.py

import sys
import os
import time
import psutil
import gc
import random
from aurora_engine.database.db_manager import DatabaseManager
from aurora_engine.database.schema import DatabaseSchema
from game.ai.ai_generator import AIContentGenerator
from game.systems.world_generator import WorldGenerator

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def run_stress_test():
    print("Starting Memory Stress Test...")
    
    # Setup DB
    db_path = 'stress_test.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        
    db_manager = DatabaseManager({'database': db_path}) # SQLite fallback if dict passed without host
    # Actually DatabaseManager expects dict for MySQL or path string for SQLite in my previous implementations?
    # Let's check DatabaseManager implementation.
    # It expects a dict. If 'host' is present it tries MySQL.
    # Wait, I changed DatabaseManager to ONLY support MySQL in the last major refactor.
    # But for a stress test, maybe we want to test the logic, not the DB connection overhead?
    # If I use the MySQL config, it will work.
    
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': 'CeneX_1234',
        'database': 'rifted_stress_test',
        'port': 3306
    }
    
    try:
        db_manager = DatabaseManager(db_config)
        db_manager.connect()
    except Exception as e:
        print(f"Failed to connect to MySQL: {e}")
        return

    # Reset DB
    DatabaseSchema.drop_tables(db_manager)
    DatabaseSchema.create_tables(db_manager)
    
    ai_generator = AIContentGenerator(db_manager)
    world_gen = WorldGenerator(db_manager, ai_generator)
    
    dim_id = "dim_stress"
    world_gen.get_or_create_dimension(dim_id, 123)
    
    start_mem = get_memory_usage()
    print(f"Initial Memory: {start_mem:.2f} MB")
    
    chunks_generated = 0
    
    try:
        while True:
            # Generate a batch of chunks
            for _ in range(50):
                x = random.randint(-1000, 1000)
                y = random.randint(-1000, 1000)
                
                # This generates data and caches it in world_gen.known_regions
                world_gen.generate_region(dim_id, x, y)
                chunks_generated += 1
            
            # Clear cache to simulate unloading/memory pressure
            # If we don't clear this, memory WILL go up linearly (expected behavior of cache)
            # We want to see if it leaks AFTER clearing.
            world_gen.known_regions.clear()
            
            # Force GC
            gc.collect()
            
            current_mem = get_memory_usage()
            diff = current_mem - start_mem
            
            print(f"Chunks: {chunks_generated} | Mem: {current_mem:.2f} MB (+{diff:.2f} MB)")
            
            # Optional: Sleep to not kill CPU
            # time.sleep(0.1)
            
            if chunks_generated >= 5000:
                break
                
    except KeyboardInterrupt:
        print("Test stopped.")
    finally:
        db_manager.disconnect()
        print("Test finished.")

if __name__ == "__main__":
    run_stress_test()
