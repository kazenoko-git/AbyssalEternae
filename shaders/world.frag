#version 150
/*
 * WORLD SHADER (Stylized, Non-Toon)
 *
 * - Uses a Half-Lambert lighting model to prevent completely black shadows,
 *   giving terrain a softer, more stylized look.
 * - Integrates with the global shadow map.
 * - Implements 2x2 PCF for soft shadow edges.
 */

// Inputs from Vertex Shader
in vec3 v_world_normal;
in vec4 v_world_pos;
in vec4 v_shadow_pos; // Position of the fragment in light space

// Panda3D-provided Uniforms (via setShaderAuto)
uniform mat4 p3d_ViewMatrix;
uniform struct p3d_LightSourceParameters {
    vec4 color;
    vec4 ambient;
    // ... other members we don't need
    sampler2DShadow shadowMap;
    mat4 shadowViewMatrix; // World to Light's Clip Space
    vec4 position; // For directional lights, .xyz is the vector TO the light
} p3d_LightSource[1];

// Per-Mesh Uniforms
uniform vec4 u_color;
uniform bool receive_shadows; // Set from Python to control shadow reception

out vec4 fragColor;

// --- Shadow Calculation (PCF) ---
float calculate_shadow_factor() {
    if (!receive_shadows) {
        return 1.0;
    }

    // v_shadow_pos is in light's clip space.
    // We need to perform perspective divide to get Normalized Device Coords [0, 1].
    vec3 shadow_coord = v_shadow_pos.xyz / v_shadow_pos.w;

    // The coordinate is now in [-1, 1] range. Transform to [0, 1] for texture lookup.
    shadow_coord = shadow_coord * 0.5 + 0.5;
    
    // If the fragment is outside the shadow map's frustum, it should not be shadowed.
    if (shadow_coord.z > 1.0) {
        return 1.0;
    }
    
    // PCF (Percentage-Closer Filtering) for soft shadows
    // We take multiple samples from the shadow map and average the results.
    float shadow = 0.0;
    float bias = 0.002; // Prevents shadow acne
    vec2 texel_size = 1.0 / textureSize(p3d_LightSource[0].shadowMap, 0);

    // 2x2 PCF Sample Pattern
    for (int x = -1; x <= 1; x += 2) {
        for (int y = -1; y <= 1; y += 2) {
            // texture() on a sampler2DShadow performs the depth comparison automatically.
            // It returns 1.0 if the fragment is lit, 0.0 if shadowed.
            shadow += texture(
                p3d_LightSource[0].shadowMap,
                vec3(shadow_coord.xy + vec2(x, y) * texel_size, shadow_coord.z - bias)
            );
        }
    }
    
    return shadow / 4.0;
}


void main() {
    // --- 1. Get Material & Lighting Properties ---
    vec3 N = normalize(v_world_normal);
    vec3 L = normalize(p3d_LightSource[0].position.xyz); // Direction TO light
    
    vec3 base_color = u_color.rgb;
    vec3 ambient_light = p3d_LightSource[0].ambient.rgb;
    vec3 directional_light = p3d_LightSource[0].color.rgb;

    // --- 2. Calculate Lighting ---
    
    // Half-Lambert lighting model.
    // The dot product is scaled from [-1, 1] to [0, 1] and squared.
    // This creates a gentle brightness falloff and prevents the unlit side
    // from being pitch black, which is ideal for stylized terrain.
    float NdotL = dot(N, L);
    float half_lambert = (NdotL * 0.5) + 0.5;
    float diffuse_intensity = half_lambert * half_lambert;

    // --- 3. Calculate Shadows ---
    float shadow_factor = calculate_shadow_factor();

    // --- 4. Combine Lighting and Shadows ---
    
    // The final lit color is a combination of ambient light and the
    // directional light, which is masked by the shadow factor.
    vec3 final_lighting = ambient_light + (diffuse_intensity * directional_light * shadow_factor);
    
    vec3 final_color = base_color * final_lighting;
    
    fragColor = vec4(final_color, u_color.a);
}
