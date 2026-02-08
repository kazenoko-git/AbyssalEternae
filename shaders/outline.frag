#version 150

uniform vec4 u_outline_color;

out vec4 fragColor;

void main() {
    fragColor = u_outline_color;
}