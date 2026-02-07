#version 150
/*
 * CHARACTER SHADER (Toon / Cel)
 *
 * - Uses quantized lighting to create distinct "bands" of light and shadow.
 * - Receives hard-edged real-time shadows from the global shadow map.
 * - Adds a Fresnel-based rim light for a classic anime look.
 */

// Inputs from Vertex Shader
in vec3 v_world_normal;
in vec4 v_world_pos;
in vec4 v_shadow_pos; // Position of the fragment in light space

// Panda3D-provided Uniforms
uniform mat4 p3d_CameraMatrix; // Inverse of the view matrix

// --- Manually passed light uniforms ---
uniform struct p3d_LightSourceParameters {
    vec4 color;
    vec4 ambient;
    sampler2DShadow shadowMap;
    vec4 position;
} u_ambient_light, u_directional_light;

// Per-Mesh Uniforms
uniform vec4 u_color;
uniform bool receive_shadows;

out vec4 fragColor;

// --- Shadow Calculation (Hard Edge) ---
float calculate_shadow_factor() {
    if (!receive_shadows) {
        return 1.0;
    }

    vec3 shadow_coord = v_shadow_pos.xyz / v_shadow_pos.w;
    shadow_coord = shadow_coord * 0.5 + 0.5;
    
    if (shadow_coord.z > 1.0) {
        return 1.0;
    }

    float bias = 0.002;
    return texture(u_directional_light.shadowMap, vec3(shadow_coord.xy, shadow_coord.z - bias));
}

void main() {
    // --- 1. Get Material & Lighting Properties ---
    vec3 N = normalize(v_world_normal);
    vec3 L = normalize(u_directional_light.position.xyz);
    vec3 V = normalize(p3d_CameraMatrix[3].xyz - v_world_pos.xyz); // Eye vector

    vec3 base_color = u_color.rgb;
    vec3 ambient_light_color = u_ambient_light.color.rgb;
    vec3 directional_light_color = u_directional_light.color.rgb;

    // --- 2. Calculate Toon Lighting ---
    float NdotL = dot(N, L);
    float light_intensity = (NdotL * 0.5) + 0.5;

    const float num_bands = 3.0;
    float quantized_intensity = floor(light_intensity * num_bands) / num_bands;
    quantized_intensity = max(quantized_intensity, 0.1);

    // --- 3. Calculate Shadows ---
    float shadow_factor = calculate_shadow_factor();

    // --- 4. Calculate Rim Light (Fresnel) ---
    float rim_dot = 1.0 - dot(V, N);
    float rim_amount = smoothstep(0.6, 1.0, rim_dot);
    rim_amount *= shadow_factor; 
    vec3 rim_color = directional_light_color * rim_amount * 0.7;

    // --- 5. Combine Lighting, Shadows, and Rim ---
    vec3 diffuse = directional_light_color * quantized_intensity * shadow_factor;
    vec3 final_lighting = ambient_light_color + diffuse + rim_color;
    vec3 final_color = base_color * final_lighting;
    
    fragColor = vec4(final_color, u_color.a);
}
