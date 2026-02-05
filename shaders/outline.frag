#version 150

uniform vec4 outline_color;

out vec4 fragColor;

void main() {
    fragColor = outline_color;
}