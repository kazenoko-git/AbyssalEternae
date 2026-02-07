#version 150

in vec3 v_world_normal;
in vec4 v_world_pos;
in vec4 v_shadow_pos;

uniform vec4 u_color;
uniform vec3 u_light_dir; // Direction TO the light source (World Space)
uniform vec3 u_view_pos;  // Camera Position (World Space)
uniform vec3 u_ambient_color; // Ambient light color

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

    // Half-Lambert Lighting (Valve style)
    // Scales [-1, 1] dot product to [0, 1] range, but squared for softer falloff
    // Prevents harsh blacks on terrain backfaces
    float NdotL = dot(N, L);
    float halfLambert = (NdotL * 0.5) + 0.5;
    float lightIntensity = halfLambert * halfLambert;

    // Shadow Calculation
    // Apply bias to prevent shadow acne
    float bias = 0.002;
    vec4 shadow_coord = v_shadow_pos;
    shadow_coord.z -= bias * shadow_coord.w;

    // textureProj performs perspective divide and depth comparison
    float shadow = textureProj(p3d_LightSource[0].shadowMap, shadow_coord);

    // Mix shadow with ambient
    // Shadows shouldn't be pitch black. We want them to be tinted by ambient.
    // If shadow is 0 (occluded), we only get ambient.
    // If shadow is 1 (lit), we get full light.

    // Combine lighting
    vec3 lightColor = p3d_LightSource[0].color.rgb;
    vec3 diffuse = lightColor * lightIntensity * shadow;

    // Add ambient (ensure it's not too strong to wash out shadows)
    vec3 ambient = u_ambient_color * 0.5;

    vec3 finalLighting = ambient + diffuse;

    // Apply to surface color
    vec3 finalColor = u_color.rgb * finalLighting;

    fragColor = vec4(finalColor, u_color.a);
}
