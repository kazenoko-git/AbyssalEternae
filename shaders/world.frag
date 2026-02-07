#version 150
/*
 * WORLD SHADER (Stylized, Non-Toon)
 *
 * - Uses a Half-Lambert lighting model to prevent completely black shadows.
 * - Integrates with the global shadow map.
 * - Implements 2x2 PCF for soft shadow edges.
 */

// Inputs from Vertex Shader
in vec3 v_world_normal;
in vec4 v_world_pos;
in vec4 v_shadow_pos; // Position of the fragment in light space

// --- Manually passed light uniforms ---
// When a shader is set manually, Panda3D's p3d_LightSource[] is not populated.
// Instead, we pass the NodePaths to the lights and let Panda3D fill these structs.
uniform struct p3d_LightSourceParameters {
    vec4 color;
    vec4 ambient;
    sampler2DShadow shadowMap;
    vec4 position; // For directional lights, .xyz is the vector TO the light
} u_ambient_light, u_directional_light;

// Per-Mesh Uniforms
uniform vec4 u_color;
uniform bool receive_shadows; // Set from Python to control shadow reception

out vec4 fragColor;

// --- Shadow Calculation (PCF) ---
float calculate_shadow_factor() {
    if (!receive_shadows) {
        return 1.0;
    }

    vec3 shadow_coord = v_shadow_pos.xyz / v_shadow_pos.w;
    shadow_coord = shadow_coord * 0.5 + 0.5;
    
    if (shadow_coord.z > 1.0) {
        return 1.0;
    }
    
    float shadow = 0.0;
    float bias = 0.002;
    vec2 texel_size = 1.0 / textureSize(u_directional_light.shadowMap, 0);

    for (int x = -1; x <= 1; x += 2) {
        for (int y = -1; y <= 1; y += 2) {
            shadow += texture(
                u_directional_light.shadowMap,
                vec3(shadow_coord.xy + vec2(x, y) * texel_size, shadow_coord.z - bias)
            );
        }
    }
    
    return shadow / 4.0;
}

void main() {
    // --- 1. Get Material & Lighting Properties ---
    vec3 N = normalize(v_world_normal);
    vec3 L = normalize(u_directional_light.position.xyz); // Direction TO light
    
    vec3 base_color = u_color.rgb;
    // For an ambient light, its contribution is stored in its 'color' property
    vec3 ambient_light = u_ambient_light.color.rgb; 
    vec3 directional_light_color = u_directional_light.color.rgb;

    // --- 2. Calculate Lighting (Half-Lambert) ---
    float NdotL = dot(N, L);
    float half_lambert = (NdotL * 0.5) + 0.5;
    float diffuse_intensity = half_lambert * half_lambert;

    // --- 3. Calculate Shadows ---
    float shadow_factor = calculate_shadow_factor();

    // --- 4. Combine Lighting and Shadows ---
    vec3 final_lighting = ambient_light + (diffuse_intensity * directional_light_color * shadow_factor);
    
    vec3 final_color = base_color * final_lighting;
    
    fragColor = vec4(final_color, u_color.a);
}
