#version 150

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform float outline_width;

in vec4 p3d_Vertex;
in vec3 p3d_Normal;

void main() {
    // Extrude vertex along normal
    vec4 pos = p3d_Vertex;
    pos.xyz += p3d_Normal * outline_width;
    
    gl_Position = p3d_ModelViewProjectionMatrix * pos;
}