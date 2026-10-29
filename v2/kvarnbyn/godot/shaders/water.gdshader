shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform vec4 water_color : source_color = vec4(0.11, 0.19, 0.18, 1.0);
uniform float flow_speed = 0.7;
uniform float ripple_strength = 0.035;
varying vec2 world_xz;

float noise2(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    float a = fract(sin(dot(i, vec2(127.1, 311.7))) * 43758.5453);
    float b = fract(sin(dot(i + vec2(1.0, 0.0), vec2(127.1, 311.7))) * 43758.5453);
    float c = fract(sin(dot(i + vec2(0.0, 1.0), vec2(127.1, 311.7))) * 43758.5453);
    float d = fract(sin(dot(i + vec2(1.0, 1.0), vec2(127.1, 311.7))) * 43758.5453);
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

void vertex() {
    world_xz = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

void fragment() {
    vec2 flow = world_xz * vec2(1.2, 2.7) + vec2(TIME * flow_speed * 0.24, -TIME * flow_speed);
    float broad = noise2(flow);
    float small = noise2(flow * 3.0 + vec2(TIME * 0.4, 0.0));
    float ripple_x = sin(flow.x * 6.4 + small * 4.0);
    float ripple_y = cos(flow.y * 5.1 + broad * 4.5);
    ALBEDO = water_color.rgb * (0.93 + 0.12 * broad) + vec3(0.009 * small);
    METALLIC = 0.06;
    ROUGHNESS = 0.20 + small * 0.12;
    SPECULAR = 0.55;
    NORMAL_MAP = vec3(ripple_x * ripple_strength, ripple_y * ripple_strength, 1.0) * 0.5 + 0.5;
    NORMAL_MAP_DEPTH = 0.65;
}
