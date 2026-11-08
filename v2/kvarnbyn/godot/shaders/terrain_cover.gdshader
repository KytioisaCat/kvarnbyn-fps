shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

// GLB colors encode rock exposure / woodland floor. Rock is projected in
// world space on three axes, so a cliff never stretches a top-down texture.
uniform sampler2D rock_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rock_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float rock_tile_m = 1.5;
uniform float grass_tile_m = 2.51;
varying vec3 world_position;
varying vec3 world_normal;

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}

void fragment() {
	vec3 n = normalize(world_normal);
	vec3 weights = pow(abs(n), vec3(4.0));
	weights /= max(dot(weights, vec3(1.0)), 0.001);
	vec3 p = world_position / rock_tile_m;
	vec3 rock = texture(rock_albedo, p.zy).rgb * weights.x
		+ texture(rock_albedo, p.xz).rgb * weights.y
		+ texture(rock_albedo, p.xy).rgb * weights.z;
	// A second, larger scale keeps a distant face readable instead of turning
	// the metre-sized grain into a uniform brown patch. Neutral weathered grey
	// is an art approximation, not a claim about measured local geology.
	vec3 macro = texture(rock_albedo, p.zy * 0.19 + vec2(0.37, 0.61)).rgb * weights.x
		+ texture(rock_albedo, p.xz * 0.19 + vec2(0.37, 0.61)).rgb * weights.y
		+ texture(rock_albedo, p.xy * 0.19 + vec2(0.37, 0.61)).rgb * weights.z;
	float tone = dot(rock, vec3(0.2126, 0.7152, 0.0722));
	rock = mix(rock, vec3(tone) * vec3(0.94, 0.99, 1.04), 0.75);
	float broad_tone = dot(macro, vec3(0.2126, 0.7152, 0.0722));
	rock *= mix(0.7, 1.2, smoothstep(0.09, 0.3, broad_tone));
	vec3 grass = texture(grass_albedo, world_position.xz / grass_tile_m).rgb;
	grass *= mix(vec3(1.0), vec3(0.53, 0.57, 0.36), smoothstep(0.15, 0.8, COLOR.g));
	float exposed = smoothstep(0.07, 0.55, COLOR.r);
	ALBEDO = mix(grass, rock, exposed);
	ROUGHNESS = 0.94;
	SPECULAR = 0.22;
	vec3 nx = texture(rock_normal, p.zy).xyz * 2.0 - 1.0;
	vec3 ny = texture(rock_normal, p.xz).xyz * 2.0 - 1.0;
	vec3 nz = texture(rock_normal, p.xy).xyz * 2.0 - 1.0;
	vec3 detail = normalize(vec3(nx.z * sign(n.x), nx.y, nx.x) * weights.x
		+ vec3(ny.x, ny.z * sign(n.y), ny.y) * weights.y
		+ vec3(nz.x, nz.y, nz.z * sign(n.z)) * weights.z);
	NORMAL = normalize((VIEW_MATRIX * vec4(normalize(mix(n, detail, exposed * 0.45)), 0.0)).xyz);
}
