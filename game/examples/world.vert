#version 150

// Uniforms from Panda3D
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat3 p3d_NormalMatrix;

// Custom Uniforms
uniform mat4 u_light_mvp; // Light View Projection

// Inputs
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec2 p3d_MultiTexCoord0;

// Outputs
out vec3 v_normal;
out vec2 v_uv;
out vec4 v_shadow_pos;
out vec3 v_world_pos;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    
    v_normal = normalize(p3d_NormalMatrix * p3d_Normal);
    v_uv = p3d_MultiTexCoord0;
    
    vec4 world_pos = p3d_ModelMatrix * p3d_Vertex;
    v_world_pos = world_pos.xyz;
    v_shadow_pos = u_light_mvp * world_pos;
}