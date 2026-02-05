#version 150

in vec3 v_world_normal;
in vec4 v_world_pos;
in vec4 v_shadow_pos;

uniform vec4 u_color;
uniform vec3 u_light_dir; // Direction TO the light source (World Space)
uniform vec3 u_view_pos;  // Camera Position (World Space)

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

out vec4 fragColor;

void main() {
     vec3 N = normalize(v_world_normal);
     vec3 L = normalize(u_light_dir);

     // Diffuse Lighting
     float NdotL = dot(N, L);

     // Shadow Calculation
     // textureProj performs perspective divide and depth comparison
     float shadow = textureProj(p3d_LightSource[0].shadowMap, v_shadow_pos);

     // Toon Quantization (Cel Shading)
     // Combine NdotL with shadow
     float lightVal = NdotL * shadow;

     float intensity;
     if (lightVal > 0.8) intensity = 1.0;
     else if (lightVal > 0.4) intensity = 0.7;
     else if (lightVal > 0.0) intensity = 0.35;
     else intensity = 0.2;

     // Simple Rim Light
     vec3 V = normalize(u_view_pos - v_world_pos.xyz);
     float NdotV = dot(N, V);
     float rim = 1.0 - max(NdotV, 0.0);
     rim = smoothstep(0.7, 0.8, rim) * 0.5;
     // Mask rim light by shadow (optional, but looks better)
     rim *= shadow;

     vec3 finalColor = (u_color.rgb * intensity) + rim;

     fragColor = vec4(finalColor, u_color.a);
}