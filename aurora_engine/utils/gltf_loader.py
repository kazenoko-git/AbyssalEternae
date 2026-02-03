import json
import struct
import os
import uuid
import logging
import hashlib
from panda3d.core import Filename, NodePath
from aurora_engine.core.logging import get_logger

logger = get_logger()

# Global cache for fixed file paths: original_abs_path -> fixed_temp_abs_path
_FIXED_FILE_CACHE = {}

def load_gltf_fixed(loader, file_path: str, keep_temp_file: bool = False):
    """
    Loads a GLTF/GLB file, fixing common issues like missing bufferViews.
    Rewrites the file to a temporary location, loads it, and returns the NodePath.
    
    Args:
        loader: The Panda3D loader instance.
        file_path: Path to the GLTF/GLB file.
        keep_temp_file: If True, the temporary fixed file is NOT deleted, and the function returns (NodePath, temp_file_path).
                        If False (default), it returns just NodePath.
    """
    # Resolve absolute path
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check Cache
    global _FIXED_FILE_CACHE
    temp_path = None
    cached = False
    
    if file_path in _FIXED_FILE_CACHE:
        temp_path = _FIXED_FILE_CACHE[file_path]
        if os.path.exists(temp_path):
            cached = True
            # logger.debug(f"Using cached fixed GLTF: {temp_path}")
        else:
            # Cache invalid
            del _FIXED_FILE_CACHE[file_path]
    
    if not cached:
        # Generate a deterministic temp path based on file hash or path hash
        # Using path hash is faster but less safe if file content changes. 
        # For dev, let's use path hash + mtime to invalidate if file changed.
        mtime = os.path.getmtime(file_path)
        path_hash = hashlib.md5(f"{file_path}_{mtime}".encode('utf-8')).hexdigest()
        
        temp_filename = f"{os.path.basename(file_path)}.{path_hash}.fixed"
        
        # Use a dedicated cache directory
        # Try to use 'cache' directory in project root
        # Assuming project root is 2 levels up from this file (aurora_engine/utils/gltf_loader.py)
        # But safer to use a relative path from CWD if possible, or just a known cache dir
        
        cache_dir = os.path.abspath("cache")
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir)
            except:
                # Fallback to temp dir if we can't create 'cache'
                import tempfile
                cache_dir = tempfile.gettempdir()
        
        temp_path = os.path.join(cache_dir, temp_filename)
        
        # Determine extension
        is_glb = False
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header == b'glTF':
                is_glb = True
                if not temp_path.endswith(".glb"): temp_path += ".glb"
            else:
                if not temp_path.endswith(".gltf"): temp_path += ".gltf"

        try:
            # Only process if it doesn't exist (it might exist from a previous run)
            if not os.path.exists(temp_path):
                logger.debug(f"Processing GLTF/GLB: {file_path} -> {temp_path}")
                if is_glb:
                    _process_glb(file_path, temp_path)
                else:
                    _process_gltf(file_path, temp_path)
            
            # Update cache
            _FIXED_FILE_CACHE[file_path] = temp_path
            
        except Exception as e:
            logger.error(f"Failed to fix GLTF {file_path}: {e}")
            raise

    try:
        # Load the fixed file
        p3d_path = Filename.fromOsSpecific(temp_path)
        
        # Load model using the provided loader
        # ENABLE CACHE: We now use a deterministic filename, so Panda3D can safely cache this!
        model = loader.loadModel(p3d_path) 
        
        if keep_temp_file:
            return model, temp_path
        else:
            return model
        
    except Exception as e:
        logger.error(f"Failed to load fixed GLTF {file_path}: {e}")
        raise
    finally:
        # Cleanup logic changed:
        # We NEVER delete the temp file immediately if we are caching it.
        # We rely on OS cleanup or manual cleanup.
        # If keep_temp_file is False, we *could* delete it, but that defeats the purpose of caching for other instances.
        # So we basically ignore keep_temp_file=False for deletion purposes, 
        # keep_temp_file now just controls the return signature.
        pass

def _process_glb(input_path, output_path):
    with open(input_path, 'rb') as f:
        data = f.read()
        
    # Parse GLB Header
    if len(data) < 12:
        raise ValueError("File too short to be GLB")
        
    magic, version, length = struct.unpack('<III', data[:12])
    
    if magic != 0x46546C67: # 'glTF'
        raise ValueError("Invalid GLB magic")
        
    chunk_pos = 12
    json_data = None
    binary_body = None
    
    # Iterate chunks
    while chunk_pos < length:
        if chunk_pos + 8 > len(data):
            break
            
        chunk_len, chunk_type = struct.unpack('<II', data[chunk_pos:chunk_pos+8])
        chunk_data = data[chunk_pos+8 : chunk_pos+8+chunk_len]
        
        if chunk_type == 0x4E4F534A: # JSON
            try:
                json_str = chunk_data.decode('utf-8')
                json_data = json.loads(json_str)
            except Exception as e:
                raise ValueError(f"Failed to parse GLB JSON: {e}")
        elif chunk_type == 0x004E4942: # BIN
            binary_body = chunk_data
            
        chunk_pos += 8 + chunk_len
        
    if json_data is None:
        raise ValueError("GLB file missing JSON chunk")
        
    # Apply fixes
    _apply_fixes(json_data)
    
    # Write GLB
    _write_glb(json_data, binary_body, output_path)

def _process_gltf(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        
    # Apply fixes
    _apply_fixes(json_data)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)

def _apply_fixes(json_data):
    """Apply known fixes to GLTF data."""
    # Ensure buffers and bufferViews exist
    if 'buffers' not in json_data:
        json_data['buffers'] = []
    if 'bufferViews' not in json_data:
        json_data['bufferViews'] = []
        
    # Check if we need to fix accessors
    needs_dummy = False
    if 'accessors' in json_data:
        for acc in json_data['accessors']:
            if 'bufferView' not in acc:
                needs_dummy = True
                break
    
    dummy_bv_index = 0
    if needs_dummy:
        # Create a dummy buffer if needed
        if len(json_data['buffers']) == 0:
            json_data['buffers'].append({
                "byteLength": 0
            })
        
        # Create a new dummy bufferView at the end
        dummy_bv_index = len(json_data['bufferViews'])
        json_data['bufferViews'].append({
            "buffer": 0,
            "byteOffset": 0,
            "byteLength": 0,
            "byteStride": 0 
        })

    if 'accessors' in json_data:
        for acc in json_data['accessors']:
            if 'bufferView' not in acc:
                acc['bufferView'] = dummy_bv_index
                if 'byteOffset' not in acc:
                    acc['byteOffset'] = 0

def _write_glb(json_data, binary_body, output_path):
    """Write GLB file."""
    # Use compact separators
    json_str = json.dumps(json_data, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    
    # Pad JSON to 4 bytes with spaces (0x20)
    json_padding = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b' ' * json_padding
    
    # Pad BIN to 4 bytes with zeros (0x00)
    if binary_body:
        bin_padding = (4 - (len(binary_body) % 4)) % 4
        binary_body += b'\x00' * bin_padding
    else:
        binary_body = b''
        
    total_length = 12 + 8 + len(json_bytes)
    if binary_body:
        total_length += 8 + len(binary_body)
        
    # Header: Magic (4) + Version (4) + Length (4)
    # Magic: 0x46546C67 (glTF)
    header = struct.pack('<III', 0x46546C67, 2, total_length)
    
    # JSON Chunk Header: Len (4) + Type (4)
    # Type: 0x4E4F534A (JSON)
    json_chunk_header = struct.pack('<II', len(json_bytes), 0x4E4F534A)
    
    with open(output_path, 'wb') as f:
        f.write(header)
        f.write(json_chunk_header)
        f.write(json_bytes)
        
        if binary_body:
            # BIN Chunk Header: Len (4) + Type (4)
            # Type: 0x004E4942 (BIN)
            bin_chunk_header = struct.pack('<II', len(binary_body), 0x004E4942)
            f.write(bin_chunk_header)
            f.write(binary_body)
