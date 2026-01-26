# ==================================================================================
# 🎨 STYLIZED SHADER (GLSL) - The "Zelda" Look
# ==================================================================================

CEL_VERT = """
#version 120
attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat3 p3d_NormalMatrix;
varying vec3 normal;
varying vec3 viewDir;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    normal = normalize(p3d_NormalMatrix * p3d_Normal);
    vec3 viewPos = (p3d_ModelViewMatrix * p3d_Vertex).xyz;
    viewDir = normalize(-viewPos);
}
"""

CEL_FRAG = """
#version 120
varying vec3 normal;
varying vec3 viewDir;
uniform vec4 p3d_ColorScale; // Used as object color

void main() {
    vec3 n = normalize(normal);
    vec3 lightDir = normalize(vec3(0.5, 1.0, 0.5)); // Fixed directional light

    // NdotL Lighting
    float NdotL = max(dot(n, lightDir), 0.0);

    // Cel Stepping
    float intensity;
    if (NdotL > 0.95) intensity = 1.0;
    else if (NdotL > 0.5) intensity = 0.8;
    else if (NdotL > 0.2) intensity = 0.5;
    else intensity = 0.3;

    // Rim Light (The "Velvet" look)
    float rim = 1.0 - max(dot(viewDir, n), 0.0);
    rim = smoothstep(0.6, 1.0, rim);
    vec3 rimColor = vec3(1.0, 1.0, 1.0) * rim * 0.4;

    vec3 finalColor = (p3d_ColorScale.rgb * intensity) + rimColor;
    gl_FragColor = vec4(finalColor, 1.0);
}
"""