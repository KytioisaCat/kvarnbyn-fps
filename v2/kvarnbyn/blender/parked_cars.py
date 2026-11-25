"""Small parked passenger cars, aligned to sampled parking surfaces."""
import math
from blender_materials import solid_material
from modelkit import color


def build(kit, collision, cars, floor):
    def mat(name, tint, roughness):
        return solid_material('Car_' + name, color(tint), roughness, .12)

    glass = mat('smoked_glass', '#414f58', .22)
    tyre = mat('rubber', '#29292b', .92)
    alloy = mat('wheel', '#a5a6a4', .48)
    headlamp = mat('headlamp', '#e4e4d7', .24)
    tail = mat('tail', '#942c36', .32)
    for car in cars:
        x, z = car['centre_xz']
        angle = math.radians(car['axis_degrees'])
        dx, dz = math.cos(angle), math.sin(angle)
        length = car['length_m']
        wheelbase = .30 * length
        track = .76
        def ground_at(s, t):
            return floor(x + dx*s + dz*t, z + dz*s - dx*t)

        wheels = {(s,t): ground_at(s,t) for s in (-wheelbase,wheelbase) for t in (-track,track)}
        mean = sum(wheels.values()) / 4
        pitch = sum(h*s for (s,t),h in wheels.items()) / (4*wheelbase**2)
        roll = sum(h*t for (s,t),h in wheels.items()) / (4*track**2)
        def point(s, t, h):
            return (x+dx*s+dz*t, -z-dz*s+dx*t, mean+pitch*s+roll*t+h)

        paint = mat(car['paint'][1:], car['paint'], .36)
        name = 'ParkedCar_' + car['id']
        def panel(material, vertices, physical=False):
            points = [point(*v) for v in vertices]
            kit.face(name, material, points)
            if physical:
                kit.face('COL_' + name, collision, points)

        # Each ring is ordered counterclockwise viewed from above.
        def ring(back, front, width, height, bevel):
            return [(s*length,t,height) for s,t in [
                (back,-width+bevel),(back+bevel/length,-width),
                (front-bevel/length,-width),(front,-width+bevel),
                (front,width-bevel),(front-bevel/length,width),
                (back+bevel/length,width),(back,width-bevel)]]

        rings = [ring(-.48,.48,.80,.33,.15), ring(-.50,.50,.88,.58,.16),
                 ring(-.48,.48,.85,.81,.13), ring(-.42,.26,.81,.86,.09),
                 ring(car['cabin_back'],.08,.65,car['height_m'],.10)]
        for level, (low, high) in enumerate(zip(rings, rings[1:])):
            for i in range(8):
                j = (i+1)%8
                panel(glass if level==3 and i%2==1 else paint,
                      [low[i],low[j],high[j],high[i]], True)
        panel(paint,rings[-1],True)
        panel(tyre,list(reversed(rings[0])),True)
        for side in (-1,1):
            for s in (-wheelbase,wheelbase):
                kit.beam(name,tyre,point(s,side*.69,.32),point(s,side*.89,.32),.32,16)
                kit.beam(name,alloy,point(s,side*.89,.32),point(s,side*.90,.32),.19,12)
            # B pillar divides the side glass at the same taper as the cabin.
            panel(tyre, [(s,side*t,h) for s,t,h in [
                (-.21,.817,.87),(-.11,.817,.87),(-.11,.655,car['height_m']),
                (-.21,.655,car['height_m'])]][::-side])
            for end, material in ((1,headlamp),(-1,tail)):
                kit.box(name,material,point(end*length*.493,side*.55,.66),
                        (.045,.30,.12),(dx,-dz),(dz,dx))
