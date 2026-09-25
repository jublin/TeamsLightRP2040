"""Check revision 3: load output_v2/round_enclosure.blend before running."""
import importlib.util
import itertools
import json
import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

path = Path(__file__).resolve().with_name("round_dome.py")
spec = importlib.util.spec_from_file_location("round_light", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
collection = bpy.data.collections[g.COLLECTION]
frame = bpy.data.objects["Round frame"]
bottom = bpy.data.objects["Service bottom with Pico cradle"]
dome = bpy.data.objects["Translucent dome"]
parts = [frame, bottom, dome]
assert all(obj.name in bpy.context.scene.objects for obj in parts)
bpy.context.view_layer.update()
report = {"topology": {obj.name: g.validate(obj) for obj in parts}}
frame_radius = max(math.hypot(vertex.co.x, vertex.co.y) for vertex in frame.data.vertices)
bottom_radius = max(math.hypot(vertex.co.x, vertex.co.y) for vertex in bottom.data.vertices)
inset_step = frame_radius - bottom_radius
assert inset_step >= g.BASE_INSET_DEPTH - 0.01, inset_step
report["inset_seam_radial_step_mm"] = round(inset_step, 3)


def duplicate(obj):
    clone = obj.copy()
    clone.data = obj.data.copy()
    collection.objects.link(clone)
    return clone


def check_empty(first, second, operation, label):
    result, cutter = duplicate(first), duplicate(second)
    g.boolean(result, cutter, operation)
    mesh = bmesh.new()
    mesh.from_mesh(result.data)
    volume = abs(mesh.calc_volume())
    mesh.free()
    bpy.data.objects.remove(result, do_unlink=True)
    report[label] = round(volume, 6)
    assert volume < 0.002, f"{label}: {volume} mm3"


for first, second in itertools.combinations(parts, 2):
    check_empty(first, second, "INTERSECT", f"{first.name} / {second.name} overlap_mm3")

# The entry slots are aligned at zero degrees. At the specified twist angle the
# tabs must still fit in the shallow internal grooves, with no solid collision.
locked_dome = duplicate(dome)
locked_dome.rotation_euler[2] = math.radians(g.DOME_LOCK_ANGLE_DEG)
check_empty(frame, locked_dome, "INTERSECT", "dome bayonet locked overlap_mm3")
report["dome_bayonet_lock_fit_verified"] = True

# Only the functional cradle is retained; the square walls are deliberately gone.
source = g.import_stl(path.parent.parent / "rpi_2040_zero_bottomv2.stl", "source", collection)
crop = g.box("crop", (-11.16, -9.01, -0.1), (11.16, 17.5, 10.001), collection)
g.boolean(source, crop, "INTERSECT")
for vertex in source.data.vertices:
    vertex.co.y += g.PICO_SHIFT_Y
check_empty(source, bottom, "DIFFERENCE", "functional_cradle_removed_mm3")

# Clearance envelopes inferred from the old mounts, NOT exact electronic CAD.
envelopes = {
    "Pico PCB envelope": ((-9.15, g.PICO_SHIFT_Y - 6, 10.01),
                          (9.15, g.PICO_SHIFT_Y + 17.499, 11.6)),
    "JST connector allowance": ((-8.5, g.PICO_SHIFT_Y - 8.7, 11.6),
                                (8.5, g.PICO_SHIFT_Y - 0.7, 20.6)),
    "LED board and components envelope": ((-17.5, -17.5, 25.001), (17.5, 17.5, 29.0)),
}
for name, (low, high) in envelopes.items():
    envelope = g.box(name, low, high, collection)
    for part in parts:
        check_empty(part, envelope, "INTERSECT", f"{name} / {part.name} overlap_mm3")
    bpy.data.objects.remove(envelope, do_unlink=True)

# Include a projecting rounded socket, not just the PCB, in the service path.
socket = g.usb_cutter(collection)
socket.name = "USB socket allowance"
y_min = min(v.co.y for v in socket.data.vertices)
for vertex in socket.data.vertices:
    vertex.co.x *= 0.94
    vertex.co.z = 12 + (vertex.co.z - 12) * 0.9
    vertex.co.y = (17 + g.PICO_SHIFT_Y if abs(vertex.co.y - y_min) < 0.01
                   else 19 + g.PICO_SHIFT_Y - 0.01)
for part in parts:
    check_empty(part, socket, "INTERSECT", f"USB socket / {part.name} overlap_mm3")

# Check the removable bottom, PCB, socket and JST space at half-mm steps.
# The LED board installs from above and does not accompany the moving bottom.
pcb = g.box("Pico insertion envelope", *envelopes["Pico PCB envelope"], collection)
jst = g.box("JST insertion envelope", *envelopes["JST connector allowance"], collection)
service = duplicate(bottom)
for moving in (pcb, jst, socket, service):
    for step in range(1, 45):
        moving.location.z = -0.5 * step
        check_empty(frame, moving, "INTERSECT",
                    f"{moving.name} insertion at {moving.location.z} mm overlap_mm3")
    bpy.data.objects.remove(moving, do_unlink=True)

for sx, sy in itertools.product((-1, 1), repeat=2):
    x, y = sx * 9.5, sy * 9.5
    hit, position, _, _ = frame.ray_cast(Vector((x, y, 30)), Vector((0, 0, -1)))
    assert hit and abs(position.z - 21) < 0.002, ("pilot bottom", position)
    hit, position, _, _ = frame.ray_cast(Vector((x + sx * 2, y, 30)), Vector((0, 0, -1)))
    assert hit and abs(position.z - 25) < 0.002, ("LED seat", position)
report["four_LED_seats_and_pilot_depths_verified"] = True
report["physical_fit_tested"] = False
report["electronic_envelopes_are_assumptions"] = True
destination = Path(bpy.data.filepath).parent / "fit_checks.json"
destination.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
