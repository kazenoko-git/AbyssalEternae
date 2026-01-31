import sys
import os
import json
import time
import sqlite3

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from aurora_engine.database.db_manager import DatabaseManager
from game.ai.ai_generator import AIContentGenerator
from aurora_engine.core.logging import get_logger

# Setup logging
logger = get_logger()

# Mock Database Manager for SQLite
class MockDatabaseManager:
    def __init__(self, db_path=":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    def connect(self): pass
    def execute(self, query, params=()):
        query = query.replace("%s", "?")
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor
    def fetch_one(self, query, params=()):
        query = query.replace("%s", "?")
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    def fetch_all(self, query, params=()):
        query = query.replace("%s", "?")
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    def commit(self): self.conn.commit()

def setup_test_db():
    db_manager = MockDatabaseManager(":memory:")
    db_manager.execute("CREATE TABLE IF NOT EXISTS npcs (npc_id TEXT PRIMARY KEY, name TEXT, role TEXT, personality_json TEXT, created_at INTEGER)")
    db_manager.execute("CREATE TABLE IF NOT EXISTS ai_cache (content_type TEXT, prompt_hash TEXT, generated_content TEXT, metadata_json TEXT, created_at INTEGER, UNIQUE(content_type, prompt_hash))")
    db_manager.execute("CREATE TABLE IF NOT EXISTS quests (quest_id TEXT PRIMARY KEY, npc_id_giver TEXT, title TEXT, description TEXT, objectives_json TEXT, rewards_json TEXT, status TEXT, created_at INTEGER)")
    db_manager.execute("CREATE TABLE IF NOT EXISTS dialogue_history (npc_id TEXT, player_line TEXT, npc_line TEXT, context_json TEXT, timestamp INTEGER)")
    db_manager.execute("CREATE TABLE IF NOT EXISTS npc_memory (memory_id INTEGER PRIMARY KEY AUTOINCREMENT, npc_id TEXT, event_type TEXT, description TEXT, emotional_impact REAL, timestamp INTEGER)")
    return db_manager

def create_test_npc(db_manager, npc_id, name, role, personality):
    personality_json = json.dumps(personality)
    db_manager.execute("INSERT INTO npcs (npc_id, name, role, personality_json, created_at) VALUES (?, ?, ?, ?, ?)", 
                      (npc_id, name, role, personality_json, int(time.time())))
    db_manager.commit()
    logger.info(f"Created test NPC: {name} ({role})")

def print_quest(quest_data):
    print("\n" + "="*60)
    print(f"QUEST: {quest_data.get('title', 'Unknown Title')}")
    print(f"Type: {quest_data.get('type', 'Unknown')}")
    print(f"Difficulty Level: {quest_data.get('recommended_level', 'N/A')}")
    print("-" * 60)
    print(f"Description: {quest_data.get('description', 'No description')}")
    print("-" * 60)
    stages = quest_data.get('stages', [])
    print(f"STAGES ({len(stages)}):")
    for stage in stages:
        print(f"\n  [Stage {stage.get('stage_id')}] {stage.get('name')}")
        print(f"  Desc: {stage.get('description')}")
        objectives = stage.get('objectives', [])
        for obj in objectives:
            print(f"    - Objective: {obj.get('type')} {obj.get('target')} (x{obj.get('count', 1)})")
    print("-" * 60)
    rewards = quest_data.get('rewards', {}) or {}
    print(f"REWARDS: XP: {rewards.get('xp', 0)}, Gold: {rewards.get('gold', 0)}")
    print("="*60 + "\n")

def main():
    logger.info("Starting Quest Generation Test...")


    db = setup_test_db()
    ai_gen = AIContentGenerator(db)

    create_test_npc(db, "npc_baker", "Martha", "Baker", {"traits": ["Kind", "Worried"]})
    create_test_npc(db, "npc_wizard", "Alaric", "Wizard", {"traits": ["Wise", "Mysterious"]})

    try:
        logger.info("Generating EASY Quest...")
        quest_easy = ai_gen.generate_quest("Pest Control", difficulty=1, npc_id="npc_baker")
        print_quest(quest_easy)

        logger.info("Generating HARD Quest...")
        quest_hard = ai_gen.generate_quest("Ancient Mystery", difficulty=10, npc_id="npc_wizard")
        print_quest(quest_hard)

    except Exception as e:
        logger.error(f"An error occurred: {e}")

    logger.info("Test Complete.")

if __name__ == "__main__":
    main()
