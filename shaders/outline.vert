#version 150

// Uniforms
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform float u_outline_width;

// Inputs
in vec4 p3d_Vertex;
in vec3 p3d_Normal;

void main() {
    // Calculate normal in view space or clip space?
    // Simple object-space extrusion works well for convex objects like spheres/cubes
    vec4 pos = p3d_Vertex;
    
    // Extrude along normal
    // Note: For hard-edged models (cube), this might split edges unless normals are smoothed.
    // But for this style, it's acceptable.
    pos.xyz += normalize(p3d_Normal) * u_outline_width;
    
    gl_Position = p3d_ModelViewProjectionMatrix * pos;
}