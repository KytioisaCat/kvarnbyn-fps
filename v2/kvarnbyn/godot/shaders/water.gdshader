shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform vec4 water_color : source_color = vec4(0.11, 0.19, 0.18, 1.0);
uniform float flow_speed = 0.7;
uniform float ripple_strength = 0.035;
uniform bool use_flow_field = false;
uniform sampler2D flow_field : filter_linear, repeat_disable;
uniform vec4 flow_bounds = vec4(-357.208, -299.812, 542.792, 400.188);
uniform float foam_strength : hint_range(0.0, 1.0) = 0.85;
uniform float flow_time = -1.0; // Native visual checks may hold a phase; normal play uses TIME.
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
    vec2 direction = normalize(vec2(-0.24, 1.0));
    float turbulence = 0.0;
    if (use_flow_field) {
        vec2 field_uv = (world_xz - flow_bounds.xy) / (flow_bounds.zw - flow_bounds.xy);
        vec3 field = texture(flow_field, field_uv).rgb;
        vec2 encoded_direction = field.rg * 2.0 - 1.0;
        if (dot(encoded_direction, encoded_direction) > 0.01) {
            direction = normalize(encoded_direction);
        }
        turbulence = field.b;
    }
    // Two short advections crossfade as either phase wraps. An unbounded
    // TIME*direction displacement stretches into contour stripes at bends.
    float clock = flow_time < 0.0 ? TIME : flow_time;
    float phase = fract(clock * flow_speed * 0.33);
    float other_phase = fract(phase + 0.5);
    float blend = abs(phase * 2.0 - 1.0);
    float travel = 2.0 + turbulence * 3.0;
    // f(position - direction*time) moves downstream. Coordinates stay in world
    // space: rotating a global position by a changing tangent distorts bends.
    vec2 p0 = world_xz - direction * phase * travel;
    vec2 p1 = world_xz - direction * other_phase * travel;
    float broad = mix(noise2(p0 * 1.6), noise2(p1 * 1.6), blend);
    float small = mix(noise2(p0 * 4.7 + vec2(7.1, 2.3)), noise2(p1 * 4.7 + vec2(7.1, 2.3)), blend);
    vec2 ripple0 = sin(p0 * vec2(6.4, 5.1) + vec2(small, broad) * 4.0);
    vec2 ripple1 = sin(p1 * vec2(6.4, 5.1) + vec2(small, broad) * 4.0);
    vec2 ripple = mix(ripple0, ripple1, blend);
    float foam = smoothstep(0.48, 0.75, broad * 0.65 + small * 0.35) * turbulence * foam_strength;
    vec3 dark_water = water_color.rgb * (0.93 + 0.12 * broad) + vec3(0.009 * small);
    ALBEDO = mix(dark_water, vec3(0.78, 0.83, 0.80), foam);
    METALLIC = mix(0.06, 0.0, foam);
    ROUGHNESS = mix(0.20 + small * 0.12, 0.82, foam);
    SPECULAR = mix(0.55, 0.25, foam);
    float wave = ripple_strength * (1.0 + turbulence * 2.0) * (1.0 - foam * 0.65);
    NORMAL_MAP = vec3(ripple * wave, 1.0) * 0.5 + 0.5;
    NORMAL_MAP_DEPTH = 0.65;
}
