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

// Panda3D-provided Uniforms (via setShaderAuto)
uniform mat4 p3d_CameraMatrix; // Inverse of the view matrix
uniform struct p3d_LightSourceParameters {
    vec4 color;
    vec4 ambient;
    sampler2DShadow shadowMap;
    mat4 shadowViewMatrix;
    vec4 position;
} p3d_LightSource[1];

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

    // A single texture lookup on a sampler2DShadow performs the depth test.
    // This gives a hard 0.0 or 1.0 value, perfect for toon shading.
    float bias = 0.002;
    return texture(p3d_LightSource[0].shadowMap, vec3(shadow_coord.xy, shadow_coord.z - bias));
}


void main() {
    // --- 1. Get Material & Lighting Properties ---
    vec3 N = normalize(v_world_normal);
    vec3 L = normalize(p3d_LightSource[0].position.xyz);
    vec3 V = normalize(p3d_CameraMatrix[3].xyz - v_world_pos.xyz); // Eye vector

    vec3 base_color = u_color.rgb;
    vec3 ambient_light = p3d_LightSource[0].ambient.rgb;
    vec3 directional_light = p3d_LightSource[0].color.rgb;

    // --- 2. Calculate Toon Lighting ---
    
    // Toon/Cel shading is achieved by quantizing the diffuse intensity.
    // The dot product gives a smooth gradient, which we force into discrete steps.
    float NdotL = dot(N, L);

    // Remap NdotL from [-1, 1] to [0, 1]
    float light_intensity = (NdotL * 0.5) + 0.5;

    // Define the number of toon bands
    const float num_bands = 3.0;
    
    // Quantize the intensity
    // The floor() function is what creates the distinct, hard-edged bands.
    float quantized_intensity = floor(light_intensity * num_bands) / num_bands;

    // Add a minimum brightness to the lit part to prevent it from being black
    quantized_intensity = max(quantized_intensity, 0.1);


    // --- 3. Calculate Shadows ---
    float shadow_factor = calculate_shadow_factor();


    // --- 4. Calculate Rim Light (Fresnel) ---
    // This adds a highlight to the edges of the model, separating it from the background.
    float rim_dot = 1.0 - dot(V, N);
    // Use smoothstep for a clean, controllable rim effect.
    float rim_amount = smoothstep(0.6, 1.0, rim_dot);
    // The rim should not appear in deep shadow.
    rim_amount *= shadow_factor; 
    vec3 rim_color = directional_light * rim_amount * 0.7; // Rim is usually less intense


    // --- 5. Combine Lighting, Shadows, and Rim ---
    
    // The final diffuse component is the directional light multiplied by the
    // toon intensity, and then fully masked by the hard shadow.
    vec3 diffuse = directional_light * quantized_intensity * shadow_factor;
    
    vec3 final_lighting = ambient_light + diffuse + rim_color;
    
    vec3 final_color = base_color * final_lighting;
    
    fragColor = vec4(final_color, u_color.a);
}
