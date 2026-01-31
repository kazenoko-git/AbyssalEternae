
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    import gltf
    print("gltf imported:", gltf)
    print("gltf dir:", dir(gltf))
    
    if hasattr(gltf, '_loader'):
        print("gltf._loader:", gltf._loader)
        print("gltf._loader dir:", dir(gltf._loader))
        
    if hasattr(gltf, '_converter'):
        print("gltf._converter:", gltf._converter)
        print("gltf._converter dir:", dir(gltf._converter))
        if hasattr(gltf._converter, 'GltfConverter'):
            print("GltfConverter found in _converter")
            
    import gltf._loader
    print("Explicit import gltf._loader:", gltf._loader)
    
    import gltf._converter
    print("Explicit import gltf._converter:", gltf._converter)

except ImportError as e:
    print("ImportError:", e)
