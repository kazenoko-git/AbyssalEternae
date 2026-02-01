import json
import struct
import os
import uuid
from panda3d.core import Filename, ModelRoot, NodePath
from aurora_engine.core.logging import get_logger

logger = get_logger()

def load_gltf_fixed(loader, file_path: str) -> NodePath:
    """
    Custom GLTF loader that fixes common issues (like missing bufferView)
    by rewriting the file to a temporary location and loading that.
    Returns a NodePath wrapping the loaded model.
    """
    # Resolve absolute path
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    # Generate a unique temp path to avoid collisions
    temp_filename = f"{os.path.basename(file_path)}.{uuid.uuid4().hex}.fixed"
    temp_dir = os.path.dirname(file_path) # Keep in same dir to resolve relative assets if any
    temp_path = os.path.join(temp_dir, temp_filename)
    
    # Determine extension for temp file
    is_glb = False
    with open(file_path, 'rb') as f:
        header = f.read(4)
        if header == b'glTF':
            is_glb = True
            temp_path += ".glb"
        else:
            temp_path += ".gltf"

    try:
        if is_glb:
            _process_glb(file_path, temp_path)
        else:
            _process_gltf(file_path, temp_path)
            
        # Load the fixed file
        p3d_path = Filename.fromOsSpecific(temp_path)
        model = loader.loadModel(p3d_path)
        return model
        
    except Exception as e:
        logger.error(f"Failed to load fixed GLTF {file_path}: {e}")
        raise
    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Could not remove temp file {temp_path}: {e}")

def _process_glb(input_path, output_path):
    with open(input_path, 'rb') as f:
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
        json.dump(json_data, f)

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
        # logger.debug(f"Created dummy bufferView at index {dummy_bv_index}")

    if 'accessors' in json_data:
        for acc in json_data['accessors']:
            if 'bufferView' not in acc:
                acc['bufferView'] = dummy_bv_index
                if 'byteOffset' not in acc:
                    acc['byteOffset'] = 0

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
