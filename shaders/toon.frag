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

    // Standard Diffuse
    float NdotL = dot(N, L);

    // Shadow Calculation
    // Apply bias to prevent shadow acne
    float bias = 0.002;
    vec4 shadow_coord = v_shadow_pos;
    shadow_coord.z -= bias * shadow_coord.w;

    float shadow = textureProj(p3d_LightSource[0].shadowMap, shadow_coord);

    // Toon Quantization (Cel Shading)
    // We use the raw NdotL for the bands, but we MASK it with the shadow.
    // This ensures shadows cut cleanly across the bands.

    // Remap NdotL to [0, 1] for easier banding logic if desired,
    // but standard [-1, 1] is fine if we check > 0.

    // Smoothstep for anti-aliased bands
    float lightVal = NdotL;

    // Band 1: Light / Shadow boundary
    // We multiply by shadow here so the shadow forces the pixel into the darkest band
    float shadowMask = smoothstep(0.0, 0.01, shadow);

    // Calculate intensity based on bands
    float intensity = 0.0;

    // High light
    float band1 = smoothstep(0.6, 0.65, lightVal);
    // Mid light
    float band2 = smoothstep(0.0, 0.05, lightVal);

    // Composite bands
    // If shadow is 0, we want the darkest color (ambient)
    // If shadow is 1, we respect the bands

    // Base ambient level for characters (usually higher than terrain to pop)
    float ambientLevel = 0.4;

    // Mix based on bands
    // 1.0 = Full Bright
    // 0.6 = Mid Tone
    // 0.0 = Shadow Tone

    float litFactor = (band1 * 0.4) + (band2 * 0.6);

    // Apply shadow: if shadowed, litFactor drops to 0
    litFactor *= shadow;

    // Final intensity is ambient + lit
    intensity = ambientLevel + litFactor;

    // Rim Light (Fresnel)
    vec3 V = normalize(u_view_pos - v_world_pos.xyz);
    float NdotV = dot(N, V);
    float rim = 1.0 - max(NdotV, 0.0);

    // Sharp rim
    rim = smoothstep(0.6, 0.7, rim);

    // Rim should only appear on the lit side or be masked?
    // Anime style often puts rim on the dark side to separate from background.
    // But usually we want it masked by self-shadowing if it's a light-rim.
    // Let's keep it simple: Rim is additive, but maybe weaker in shadow.
    rim *= 0.5;

    vec3 lightColor = p3d_LightSource[0].color.rgb;
    vec3 finalColor = (u_color.rgb * intensity * lightColor) + (rim * lightColor * 0.5);

    fragColor = vec4(finalColor, u_color.a);
}
