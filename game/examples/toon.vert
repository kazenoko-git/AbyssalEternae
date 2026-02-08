#version 150

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat3 p3d_NormalMatrix;
uniform mat4 u_light_mvp;

in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec2 p3d_MultiTexCoord0;

out vec3 v_normal;
out vec2 v_uv;
out vec4 v_shadow_pos;
out vec3 v_view_dir;

uniform vec3 p3d_ViewVector; // Camera position in model space usually, but we want world view dir

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    
    v_normal = normalize(p3d_NormalMatrix * p3d_Normal);
    v_uv = p3d_MultiTexCoord0;
    
    vec4 world_pos = p3d_ModelMatrix * p3d_Vertex;
    v_shadow_pos = u_light_mvp * world_pos;
    
    // Calculate view direction (World Space)
    // Assuming camera position is passed or derived. 
    // For simplicity in this setup, we'll approximate or rely on uniforms.
    // Actually, let's just pass the camera pos as uniform in Python.
}