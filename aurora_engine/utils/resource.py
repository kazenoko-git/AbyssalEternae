import os

def resolve_path(path: str) -> str:
    """
    Resolve a resource path.
    Checks:
    1. Absolute path
    2. Relative to CWD
    3. Relative to Parent of CWD (Project Root if running from subdir)
    4. Relative to Grandparent of CWD
    """
    if not path:
        return path
        
    if os.path.isabs(path):
        return path
        
    # 1. CWD
    if os.path.exists(path):
        return os.path.abspath(path)
        
    # 2. Parent
    parent_path = os.path.join("..", path)
    if os.path.exists(parent_path):
        return os.path.abspath(parent_path)
        
    # 3. Grandparent
    grandparent_path = os.path.join("../..", path)
    if os.path.exists(grandparent_path):
        return os.path.abspath(grandparent_path)
        
    # Return original absolute path if not found (let loader fail or handle it)
    return os.path.abspath(path)
