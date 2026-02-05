#version 150

uniform struct {
  vec4 color;
  vec4 position;
  sampler2DShadow shadowMap;
  mat4 shadowViewMatrix;
} p3d_LightSource[1];

in vec3 v_view_pos;
in vec3 v_view_normal;
in vec4 v_shadow_coord;

out vec4 fragColor;

void main() {
  // 1. Check if Light Data exists
  if (length(p3d_LightSource[0].color.rgb) < 0.01) {
    fragColor = vec4(0.0, 0.0, 1.0, 1.0); // BLUE = No Light Data
    return;
  }

  // 2. Calculate Shadow
  float shadow = textureProj(p3d_LightSource[0].shadowMap, v_shadow_coord);

  // 3. Calculate Lambert
  vec3 N = normalize(v_view_normal);
  vec3 L = normalize(p3d_LightSource[0].position.xyz); // View Space Direction
  float NdotL = max(dot(N, L), 0.0);

  // 4. Output
  if (shadow < 0.5) {
     // IN SHADOW -> RED
     fragColor = vec4(1.0, 0.0, 0.0, 1.0);
  } else {
     // LIT -> WHITE (modulated by NdotL)
     fragColor = vec4(vec3(NdotL), 1.0);
  }
}
