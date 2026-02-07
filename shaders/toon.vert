#version 150

// Panda3D-provided uniforms
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat3 p3d_NormalMatrix; // View Space Normal Matrix (Unused now)

// Full Panda3D LightSource struct definition
uniform struct p3d_LightSourceParameters {
    vec4 color;
    vec4 ambient;
    vec4 diffuse;
    vec4 specular;
    vec4 position;
    vec3 spotDirection;
    float spotExponent;
    float spotCutoff;
    float spotCosCutoff;
    vec3 attenuation;
    sampler2DShadow shadowMap;
    mat4 shadowViewMatrix;
} p3d_LightSource[1];

// Vertex attributes
in vec4 p3d_Vertex;
in vec3 p3d_Normal;

// Outputs to fragment shader
out vec3 v_world_pos;
out vec3 v_world_normal;
out vec4 v_shadow_coord;

void main() {
    // Clip Space Position
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;

    // World Space Position
    v_world_pos = (p3d_ModelMatrix * p3d_Vertex).xyz;

    // World Space Normal
    // We use the Model Matrix to rotate the normal into the world.
    // Note: For non-uniform scaling, we strictly need the Inverse Transpose,
    // but for this toon style and simple shapes, this approximation is stable and prevents view-dependent artifacts.
    v_world_normal = normalize((p3d_ModelMatrix * vec4(p3d_Normal, 0.0)).xyz);

    // Shadow Coordinates
    // Transforms World Position -> Light's Clip Space
    v_shadow_coord = p3d_LightSource[0].shadowViewMatrix * vec4(v_world_pos, 1.0);
}