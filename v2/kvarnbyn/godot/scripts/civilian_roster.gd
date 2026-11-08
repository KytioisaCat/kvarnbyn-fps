extends RefCounted

# Civilian game portrayals. Heights/proportions are art direction, not measurements.
# Keep behaviour/placement here; Blender owns geometry, not gameplay configuration.
const PEOPLE := [
	{"id": "lars", "name": "Lars Gahrn", "height": 1.88, "radius": 0.23, "speed": 0.52,
	 "home": Vector3(-25, 0, -2), "heading": 0.0, "route": Vector3(1.6, 0, 0.3),
	 "lines": ["Här finns mycket att upptäcka om man tar sig tid att titta.", "Ta gärna en promenad runt torget också."]},
	{"id": "per", "name": "Per Andersson", "height": 1.80, "radius": 0.29, "speed": 0.83,
	 "home": Vector3(-31, 0, -4), "heading": 0.35, "route": Vector3(1.4, 0, -0.6),
	 "lines": ["Jag tog en liten omväg. Den blev visst ganska stor.", "Man får väl ta ett steg i taget. Helst åt rätt håll."]},
	{"id": "ronny", "name": "Ronny Jönsson", "height": 1.77, "radius": 0.38, "speed": 0.65,
	 "home": Vector3(-33, 0, 7), "heading": -0.35, "route": Vector3(1.4, 0, 0.4),
	 "lines": ["Jag står bra här. Utsikten är ju helt okej.", "Det är ingen brådska för min del."]},
	{"id": "linnea", "name": "Linnea Rönnqvist", "height": 1.69, "radius": 0.28, "speed": 0.76,
	 "home": Vector3(-15, 0, 2), "heading": 0.15, "route": Vector3(-1.3, 0, 0.5),
	 "lines": ["Jag tar en runda och ser vad som händer på torget.", "Har du hittat något intressant här i kvarteren?"]},
]
