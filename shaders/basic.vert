#version 150

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelViewMatrix;
uniform mat3 p3d_NormalMatrix;

uniform struct {
  sampler2DShadow shadowMap;
  mat4 shadowViewMatrix;
} p3d_LightSource[1];

in vec4 p3d_Vertex;
in vec3 p3d_Normal;

out vec3 v_view_pos;
out vec3 v_view_normal;
out vec4 v_shadow_coord;

void main() {
  gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;

  vec4 view_pos = p3d_ModelViewMatrix * p3d_Vertex;
  v_view_pos = view_pos.xyz;
  v_view_normal = normalize(p3d_NormalMatrix * p3d_Normal);

  // Standard Panda3D Shadow Transform
  v_shadow_coord = p3d_LightSource[0].shadowViewMatrix * view_pos;
}
