import json
import struct
import os
import time
from panda3d.core import Filename
from aurora_engine.core.logging import get_logger

logger = get_logger()

def load_gltf_fixed(loader, file_path):
    """
    Custom GLTF loader that fixes common issues (like missing bufferView)
    by rewriting the file to a temporary location and loading that.
    """
    # Resolve absolute path
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    logger.info(f"Loading GLTF/GLB with custom fixer (Repack Mode): {file_path}")
        
    # Read file header to determine type
    with open(file_path, 'rb') as f:
        header = f.read(4)
        
    try:
        if header == b'glTF':
            # It's a GLB file
            return _load_glb_repack(loader, file_path)
        else:
            # Assume GLTF (JSON)
            return _load_gltf_json_repack(loader, file_path)
    except Exception as e:
        logger.error(f"Failed to repack/load GLTF: {e}")
        raise

def _load_glb_repack(loader, file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
        
    # Parse GLB Header
    magic, version, length = struct.unpack('<III', data[:12])
    
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
                logger.error(f"Failed to parse GLB JSON: {e}")
                raise
        elif chunk_type == 0x004E4942: # BIN
            binary_body = chunk_data
            
        chunk_pos += 8 + chunk_len
        
    if json_data is None:
        raise ValueError("GLB file missing JSON chunk")
        
    # --- FIXES ---
    _apply_fixes(json_data)
    
    # --- REPACK ---
    temp_path = file_path + ".fixed.glb"
    _write_glb(json_data, binary_body, temp_path)
    
    try:
        # Load the fixed file
        # Convert to Panda filename
        p3d_path = Filename.fromOsSpecific(temp_path)
        model = loader.loadModel(p3d_path)
        return model
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                logger.warning(f"Could not remove temp file: {temp_path}")

def _load_gltf_json_repack(loader, file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        
    # --- FIXES ---
    _apply_fixes(json_data)
    
    # --- REPACK ---
    temp_path = file_path + ".fixed.gltf"
    
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f)
        
    try:
        p3d_path = Filename.fromOsSpecific(temp_path)
        model = loader.loadModel(p3d_path)
        return model
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                logger.warning(f"Could not remove temp file: {temp_path}")

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
            "byteStride": 0 # Added byteStride to prevent KeyError
        })
        logger.info(f"Created dummy bufferView at index {dummy_bv_index}")

    if 'accessors' in json_data:
        fixed_count = 0
        for acc in json_data['accessors']:
            if 'bufferView' not in acc:
                acc['bufferView'] = dummy_bv_index
                if 'byteOffset' not in acc:
                    acc['byteOffset'] = 0
                fixed_count += 1
        if fixed_count > 0:
            logger.info(f"Fixed {fixed_count} accessors missing bufferView")

def _write_glb(json_data, binary_body, output_path):
    """Write GLB file."""
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
    header = struct.pack('<III', 0x46546C67, 2, total_length)
    
    # JSON Chunk Header: Len (4) + Type (4)
    json_chunk_header = struct.pack('<II', len(json_bytes), 0x4E4F534A)
    
    with open(output_path, 'wb') as f:
        f.write(header)
        f.write(json_chunk_header)
        f.write(json_bytes)
        
        if binary_body:
            # BIN Chunk Header: Len (4) + Type (4)
            bin_chunk_header = struct.pack('<II', len(binary_body), 0x004E4942)
            f.write(bin_chunk_header)
            f.write(binary_body)
