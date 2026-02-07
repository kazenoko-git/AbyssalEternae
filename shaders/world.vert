#version 150

// Panda3D Standard Uniforms
uniform mat4 p3d_ModelMatrix;
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat3 p3d_NormalMatrix;

// Light Struct for Shadow Matrix
struct p3d_LightSourceParameters {
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
};
uniform p3d_LightSourceParameters p3d_LightSource[1];

// Vertex Inputs
in vec4 p3d_Vertex;
in vec3 p3d_Normal;

// Outputs
out vec3 v_world_normal;
out vec4 v_world_pos;
out vec4 v_shadow_pos;

void main() {
    v_world_pos = p3d_ModelMatrix * p3d_Vertex;
    v_world_normal = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);

    // Calculate Shadow Coordinate
    // shadowViewMatrix transforms from World Space to Shadow Clip Space
    v_shadow_pos = p3d_LightSource[0].shadowViewMatrix * v_world_pos;

    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
}
