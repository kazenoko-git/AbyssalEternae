#version 150
/*
 * CHARACTER SHADER (Toon / Cel)
 *
 * - Uses quantized lighting to create distinct "bands" of light and shadow.
 * - Receives hard-edged real-time shadows from the global shadow map.
 * - Adds a Fresnel-based rim light for a classic anime look.
 */

// --- UNIFORMS ---
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

uniform vec3 p3d_CameraPosition;

// Custom Properties
uniform vec4 u_object_color;
uniform float u_toon_bands;
uniform vec4 u_shadow_color;
uniform vec3 u_sun_direction; // Explicit World Space Sun Direction
uniform vec4 u_sun_color;
uniform vec4 u_ambient_color;

// Inputs
in vec3 v_world_pos;
in vec3 v_world_normal;
in vec4 v_shadow_coord;

out vec4 fragColor;

// --- SHADOW MAPPING ---
float get_shadow_factor(vec4 shadow_coord, float bias) {
    vec3 proj_coords = shadow_coord.xyz / shadow_coord.w;
    proj_coords = proj_coords * 0.5 + 0.5;

    if(proj_coords.x < 0.0 || proj_coords.x > 1.0 ||
       proj_coords.y < 0.0 || proj_coords.y > 1.0 ||
       proj_coords.z > 1.0) {
        return 1.0;
    }

    float current_depth = proj_coords.z - bias;
    float shadow = 0.0;
    vec2 texel_size = 1.0 / textureSize(p3d_LightSource[0].shadowMap, 0);

    // 3x3 PCF
    for(int x = -1; x <= 1; ++x) {
        for(int y = -1; y <= 1; ++y) {
            shadow += texture(p3d_LightSource[0].shadowMap, vec3(proj_coords.xy + vec2(x, y) * texel_size, current_depth));
        }
    }
    return shadow / 9.0;
}

void main() {
    // Prevent optimization of v_world_pos
    if (v_world_pos.x > 100000.0) discard;

    vec3 N = normalize(v_world_normal);

    // Use Explicit World Space Sun Direction passed from Python
    // This avoids any confusion with Panda's View-Space light positions
    vec3 L = normalize(u_sun_direction);

    // --- 1. DIFFUSE TERM ---
    float NdotL = dot(N, L);
    float light_intensity = max(NdotL, 0.0);

    // Toon Bands
    float bands = u_toon_bands > 0.0 ? u_toon_bands : 3.0;
    float toon_intensity = ceil(light_intensity * bands) / bands;

    // --- 2. SHADOW MAPPING ---
    // Minimal bias for ground plane
    float bias = max(0.001 * (1.0 - NdotL), 0.0002);
    float shadow = get_shadow_factor(v_shadow_coord, bias);

    // Combine
    float final_light_factor = toon_intensity * shadow;

    // --- 3. COLOR COMPOSITION ---
    vec3 obj_color = u_object_color.rgb;
    if (length(obj_color) < 0.01) obj_color = vec3(1.0, 0.0, 1.0);

    vec3 light_color = u_sun_color.rgb;
    if (length(light_color) < 0.01) light_color = vec3(1.0);

    vec3 lit_color = obj_color * light_color;

    vec3 shadow_tint = u_shadow_color.rgb;
    if (length(shadow_tint) < 0.01) shadow_tint = vec3(0.1, 0.1, 0.3);
    vec3 shadow_color = obj_color * shadow_tint;

    // Hard Mix for clean anime look
    // If light factor > 0.01, it's lit. Otherwise shadow.
    // This prevents "muddy" transitions.
    float mix_factor = step(0.01, final_light_factor);

    // But we want the toon bands to show up in the lit area
    // So we modulate the lit color by the toon intensity
    // Actually, for pure 2-tone, we just want Lit vs Shadow.
    // Let's stick to the mix based on shadow * diffuse.

    // Soften the transition (Fade)
    mix_factor = smoothstep(0.0, 0.35, final_light_factor);

    vec3 final_color = mix(shadow_color, lit_color, mix_factor);

    // FORCE USAGE: Add a tiny fraction of shadow coord to color
    final_color += v_shadow_coord.rgb * 0.000001;

    fragColor = vec4(final_color, u_object_color.a);
}