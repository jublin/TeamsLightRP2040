"""Build a compact Teams light with integrated mounts and a serviceable bottom.

Blender: open this file in the Text Editor and Run Script, or:
blender --background --python round_dome.py -- --output /path/to/output

All geometry coordinates and STL exports are millimetres. Only the generated
collection is replaced on rerun; other scene objects are left alone.
"""
import argparse
import json
import math
from pathlib import Path
import struct
import subprocess
import sys

import bpy
import bmesh
from mathutils import Vector

# Dimensions in mm. Keep the original STL files beside the blender directory.
OUTER_RADIUS = 28.0
DOME_WALL = 1.6
BASE_FLOOR = 1.5  # matches the original holder's internal floor height
SEAM_Z = 16.0
EQUATOR_Z = 28.0
DOME_RISE = 20.0
LIP_HEIGHT = 4.0
LIP_WALL = 1.6
RADIAL_FIT = 0.30  # clearance per side, not diametral
USB_WIDTH = 9.0
USB_HEIGHT = 3.5
USB_CENTER_Z = 12.0
PICO_SHIFT_Y = 5.5
LED_MOUNT_Z = 25.0
LED_HOLE_PITCH = 19.0
LED_PILOT_RADIUS = 1.2645  # measured from the original matrix holder
BOTTOM_Z = -1.5  # 3 mm service plate; source mounting Z heights stay unchanged
SERVICE_MOUNTS = [(-22.0, 0.0), (22.0, 0.0), (0.0, -22.0)]
BASE_INSET_DEPTH = 1.0
FRAME_SKIRT_CLEARANCE = 0.30
FRAME_SKIRT_BOTTOM = 0.20
DOME_LOCK_COUNT = 3
DOME_LOCK_ANGLE_DEG = 12.0
DOME_LOCK_TAB_Z = 17.0
DOME_LOCK_TAB_HEIGHT = 1.40
DOME_LOCK_TAB_WIDTH = 3.60
DOME_LOCK_TAB_INNER_RADIUS = 25.70
DOME_LOCK_TAB_OUTER_RADIUS = 26.70
DOME_LOCK_SLOT_WIDTH = 4.80
DOME_LOCK_GROOVE_WIDTH = 10.00
SEGMENTS = 192
ARC_STEPS = 64
COLLECTION = "Round Teams Light"


def arguments():
    # __file__ may be relative for an unsaved Blender Text Editor document.
    script = Path(__file__).resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, default=script.parent.parent)
    parser.add_argument("--output", type=Path, default=script.parent / "output_v2")
    parser.add_argument("--render", action="store_true")
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(tail)


def mesh_object(name, vertices, faces, collection):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.00001)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def import_stl(path, name, collection):
    """Import the repository's binary STLs without optional importer addons."""
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + 50 * count:
        raise ValueError(f"Expected a binary STL: {path}")
    vertices = [struct.unpack_from("<fff", data, 84 + i * 50 + 12 + j * 12)
                for i in range(count) for j in range(3)]
    # Each original STL was exported at a different XY print-bed offset.
    center = [(min(v[a] for v in vertices) + max(v[a] for v in vertices)) / 2
              for a in (0, 1)]
    vertices = [(x - center[0], y - center[1], z) for x, y, z in vertices]
    return mesh_object(name, vertices,
                       [(i, i + 1, i + 2) for i in range(0, len(vertices), 3)],
                       collection)


def lathe(name, profile, collection):
    """Revolve a closed radius/Z cross-section; use single vertices at poles."""
    vertices, rings, faces = [], [], []
    for radius, z in profile:
        ring = []
        for i in range(1 if abs(radius) < 1e-8 else SEGMENTS):
            angle = 2 * math.pi * i / SEGMENTS
            ring.append(len(vertices))
            vertices.append((radius * math.cos(angle), radius * math.sin(angle), z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:] + rings[:1]):
        if len(a) == len(b) == 1:
            continue
        for i in range(SEGMENTS):
            j = (i + 1) % SEGMENTS
            if len(a) == 1:
                faces.append((a[0], b[i], b[j]))
            elif len(b) == 1:
                faces.append((a[i], b[0], a[j]))
            else:
                faces.append((a[i], b[i], b[j], a[j]))
    return mesh_object(name, vertices, faces, collection)


def boolean(obj, cutter, operation):
    # Repeated cuts leave large concave n-gons on the service plate. Triangulate
    # these before the next exact boolean to avoid cracks at later screw holes.
    for operand in (obj, cutter):
        bm = bmesh.new()
        bm.from_mesh(operand.data)
        bmesh.ops.triangulate(bm, faces=[face for face in bm.faces if len(face.verts) > 4])
        bm.to_mesh(operand.data)
        bm.free()
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new(operation, "BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # Exact CSG can leave coincident vertices separated by ~1e-15 mm.
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.00001)
    bm.to_mesh(obj.data)
    bm.free()
    bpy.data.objects.remove(cutter, do_unlink=True)


def box(name, low, high, collection):
    vertices = [(x, y, z) for z in (low[2], high[2])
                for y in (low[1], high[1]) for x in (low[0], high[0])]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return mesh_object(name, vertices, faces, collection)


def rotated_box(name, low, high, angle_deg, collection):
    obj = box(name, low, high, collection)
    obj.rotation_euler[2] = math.radians(angle_deg)
    return obj


def led_bracket(x_sign, y_sign, collection):
    """An integrated 45-degree corbel: vertical outer leg, inward LED seat."""
    profile = [(18.5, BASE_FLOOR), (21.5, BASE_FLOOR),
               (21.5, LED_MOUNT_Z), (6.5, LED_MOUNT_Z),
               (6.5, LED_MOUNT_Z - 5), (18.5, LED_MOUNT_Z - 17)]
    yc = y_sign * LED_HOLE_PITCH / 2
    vertices = [(x_sign * x, y, z) for y in (yc - 3, yc + 3) for x, z in profile]
    n = len(profile)
    faces = [tuple(range(n)), tuple(range(n, n * 2))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return mesh_object("LED support bracket", vertices, faces, collection)


def usb_cutter(collection):
    """Rounded 9 x 3.5 mm USB-C port, matching the original aperture envelope."""
    radius = USB_HEIGHT / 2
    straight = USB_WIDTH / 2 - radius
    outline = []
    for side in (1, -1):
        for i in range(33):
            angle = -math.pi / 2 + math.pi * i / 32 + (0 if side == 1 else math.pi)
            outline.append((side * straight + radius * math.cos(angle),
                            USB_CENTER_Z + radius * math.sin(angle)))
    vertices = [(x, y, z) for y in (17.0 + PICO_SHIFT_Y, OUTER_RADIUS + 1) for x, z in outline]
    n = len(outline)
    faces = [tuple(range(n)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return mesh_object("USB-C aperture", vertices, faces, collection)


def validate(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bad = sum(not e.is_manifold for e in bm.edges)
    volume = bm.calc_volume(signed=True)
    unseen = set(bm.verts)
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            for edge in stack.pop().link_edges:
                for vertex in edge.verts:
                    if vertex in unseen:
                        unseen.remove(vertex)
                        stack.append(vertex)
    bm.free()
    if bad or volume <= 0 or components != 1:
        raise ValueError(f"{obj.name}: {bad} non-manifold edges, "
                         f"{components} components, volume {volume}")
    return {"non_manifold_edges": bad, "connected_components": components,
            "volume_mm3": round(volume, 3),
            "size_mm": [round(max(v.co[i] for v in obj.data.vertices) -
                              min(v.co[i] for v in obj.data.vertices), 3)
                        for i in range(3)]}


def export_stl(obj, path):
    """Local coordinates: each part rests on Z=0 in the slicer."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    floor = min(v.co.z for v in mesh.vertices)
    with path.open("wb") as stream:
        stream.write(b"Teams light; millimetres".ljust(80, b"\0"))
        stream.write(struct.pack("<I", len(mesh.loop_triangles)))
        for face in mesh.loop_triangles:
            coords = [tuple(mesh.vertices[i].co - Vector((0, 0, floor)))
                      for i in face.vertices]
            stream.write(struct.pack("<12fH", *face.normal,
                                     *(c for vertex in coords for c in vertex), 0))


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    return mat


def preview(scene, collection, parts, output):
    # Workbench studio shading intentionally avoids suggesting validated optics.
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.background_type = "WORLD"
    scene.world.color = (0.07, 0.085, 0.11)
    camera_data = bpy.data.cameras.new("Round light camera")
    camera = bpy.data.objects.new("Round light camera", camera_data)
    collection.objects.link(camera)
    camera.location = (110, 160, 115)
    target = Vector((0, 0, 23))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 85
    scene.camera = camera
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    # A dedicated scene keeps unrelated user objects out of the generated files.
    scene.render.filepath = str(output / "assembled.png")
    bpy.ops.render.render(write_still=True, scene=scene.name)
    # Inspect the actual newly integrated supports with the diffuser removed.
    parts[1].hide_render = True
    camera.location = (90, -115, 140)
    camera.rotation_euler = (Vector((0, 0, 12)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.ortho_scale = 80
    scene.render.filepath = str(output / "interior.png")
    bpy.ops.render.render(write_still=True, scene=scene.name)
    parts[1].hide_render = False
    parts[1].location.z += 38
    parts[2].location.z -= 28
    camera_data.ortho_scale = 150
    camera.location = (100, -135, 150)
    camera.rotation_euler = (Vector((0, 0, 40)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(output / "exploded.png")
    bpy.ops.render.render(write_still=True, scene=scene.name)
    parts[1].location.z -= 38
    parts[2].location.z += 28
    camera.location = (110, 160, 115)
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.ortho_scale = 85


def main():
    args = arguments()
    args.models = args.models.resolve()
    output = args.output.resolve()
    for name in ("rpi_2040_zero_bottomv2.stl", "Matrix_holderv2.stl"):
        if not (args.models / name).is_file():
            raise FileNotFoundError(f"Missing {name}; set --models to the 3DModels directory")
    inner = OUTER_RADIUS - DOME_WALL
    lip_outer = inner - RADIAL_FIT
    lip_inner = lip_outer - LIP_WALL
    service_bottom_radius = OUTER_RADIUS - BASE_INSET_DEPTH
    frame_skirt_inner = service_bottom_radius + FRAME_SKIRT_CLEARANCE
    if not (OUTER_RADIUS >= 28 and LED_MOUNT_Z >= 25 and DOME_WALL > 0 and RADIAL_FIT > 0 and LIP_WALL > 0 and
            DOME_RISE > DOME_WALL and EQUATOR_Z > SEAM_Z + LIP_HEIGHT and
            USB_CENTER_Z - USB_HEIGHT / 2 > BASE_FLOOR and
            USB_CENTER_Z + USB_HEIGHT / 2 < SEAM_Z):
        raise ValueError("Incompatible dome, joint, or USB parameters")
    output.mkdir(parents=True, exist_ok=True)
    old = bpy.data.collections.get(COLLECTION)
    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)
    collection = bpy.data.collections.new(COLLECTION)
    scene = bpy.context.scene
    scene.collection.children.link(collection)
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = "MILLIMETERS"

    # Extract only the functional low board/pin retention features. The square
    # walls, four enclosure insert towers, and entire matrix tray are discarded.
    cradle = import_stl(args.models / "rpi_2040_zero_bottomv2.stl", "Pico pin cradle", collection)
    crop = box("Functional cradle crop", (-11.16, -9.01, -0.1),
               (11.16, 17.50, 10.001), collection)
    boolean(cradle, crop, "INTERSECT")
    for vertex in cradle.data.vertices:
        vertex.co.y += PICO_SHIFT_Y
    base = lathe("Round frame", [(OUTER_RADIUS - 2.0, BASE_FLOOR), (OUTER_RADIUS, BASE_FLOOR),
                 (OUTER_RADIUS, SEAM_Z), (lip_outer, SEAM_Z),
                 (lip_outer, SEAM_Z + LIP_HEIGHT),
                 (lip_inner, SEAM_Z + LIP_HEIGHT), (lip_inner, SEAM_Z),
                 (OUTER_RADIUS - 2.0, SEAM_Z)], collection)
    skirt = lathe("Inset seam skirt", [(frame_skirt_inner, FRAME_SKIRT_BOTTOM),
                  (OUTER_RADIUS, FRAME_SKIRT_BOTTOM),
                  (OUTER_RADIUS, BASE_FLOOR + 0.05),
                  (frame_skirt_inner, BASE_FLOOR + 0.05)], collection)
    boolean(base, skirt, "UNION")
    bottom = lathe("Service bottom with Pico cradle", [(0, BOTTOM_Z),
                   (service_bottom_radius, BOTTOM_Z),
                   (service_bottom_radius, BASE_FLOOR),
                   (0, BASE_FLOOR)], collection)
    boolean(bottom, cradle, "UNION")
    for sx in (-1, 1):
        for sy in (-1, 1):
            boolean(base, led_bracket(sx, sy, collection), "UNION")
            yc = sy * LED_HOLE_PITCH / 2
            web = box("Bracket to perimeter web",
                      (19 if sx > 0 else -27, yc - 3, BASE_FLOOR),
                      (27 if sx > 0 else -19, yc + 3, 12), collection)
            boolean(base, web, "UNION")
            drill = lathe("LED screw pilot", [(0, LED_MOUNT_Z - 4),
                          (LED_PILOT_RADIUS, LED_MOUNT_Z - 4),
                          (LED_PILOT_RADIUS, LED_MOUNT_Z + 1),
                          (0, LED_MOUNT_Z + 1)], collection)
            drill.location.x = sx * LED_HOLE_PITCH / 2
            drill.location.y = sy * LED_HOLE_PITCH / 2
            boolean(base, drill, "DIFFERENCE")
    for x, y in SERVICE_MOUNTS:
        # Three reused M3 x 4 inserts enter from below. Short webs tie each
        # boss into the perimeter; no central columns cross the electronics.
        # Extend below the frame before trimming: coincident boss/frame bottoms
        # can produce open edges in Blender's exact boolean solver.
        boss = lathe("Bottom insert boss", [(0, BASE_FLOOR + 0.05), (4.5, BASE_FLOOR + 0.05),
                      (4.5, 9), (0, 9)], collection)
        boss.location.x, boss.location.y = x, y
        boolean(base, boss, "UNION")
        bore = lathe("M3 insert socket", [(0, BASE_FLOOR - 0.4),
                      (2.05, BASE_FLOOR - 0.4), (2.05, 7), (0, 7)], collection)
        bore.location.x, bore.location.y = x, y
        boolean(base, bore, "DIFFERENCE")
        through = lathe("Bottom M3 clearance", [(0, BOTTOM_Z - 1), (1.65, BOTTOM_Z - 1),
                         (1.65, BASE_FLOOR + 1), (0, BASE_FLOOR + 1)], collection)
        through.location.x, through.location.y = x, y
        boolean(bottom, through, "DIFFERENCE")
        head = lathe("Button head recess", [(0, BOTTOM_Z - 0.1), (3.2, BOTTOM_Z - 0.1),
                      (3.2, 0.3), (0, 0.3)], collection)
        head.location.x, head.location.y = x, y
        boolean(bottom, head, "DIFFERENCE")
    # The board moves toward the perimeter. A small flat port face replaces the
    # first pass's long access tunnel; retain the original aperture dimensions.
    port_inner = 17.5 + PICO_SHIFT_Y
    port_outer = 19.0 + PICO_SHIFT_Y
    # The USB face belongs to the removable bottom. A U-shaped frame opening
    # lets the real socket (which projects beyond the PCB) move out from below.
    panel = box("Service bottom USB face", (-7, port_inner, BASE_FLOOR - 0.2),
                (7, port_outer, 14), collection)
    boolean(bottom, panel, "UNION")
    boolean(bottom, usb_cutter(collection), "DIFFERENCE")
    opening = box("USB tongue clearance", (-7.3, port_inner - 0.3, BASE_FLOOR - 0.5),
                  (7.3, OUTER_RADIUS + 1, 14.3), collection)
    boolean(base, opening, "DIFFERENCE")
    outline = lathe("Circular outline trim", [(0, FRAME_SKIRT_BOTTOM - 0.10),
                    (OUTER_RADIUS, FRAME_SKIRT_BOTTOM - 0.10),
                    (OUTER_RADIUS, LED_MOUNT_Z + 1),
                    (0, LED_MOUNT_Z + 1)], collection)
    boolean(base, outline, "INTERSECT")
    for index in range(DOME_LOCK_COUNT):
        angle = index * 360.0 / DOME_LOCK_COUNT
        tab = rotated_box("Dome bayonet tab",
                          (DOME_LOCK_TAB_INNER_RADIUS, -DOME_LOCK_TAB_WIDTH / 2, DOME_LOCK_TAB_Z),
                          (DOME_LOCK_TAB_OUTER_RADIUS,
                           DOME_LOCK_TAB_WIDTH / 2,
                           DOME_LOCK_TAB_Z + DOME_LOCK_TAB_HEIGHT),
                          angle, collection)
        boolean(base, tab, "UNION")

    outer_arc, inner_arc = [], []
    for i in range(ARC_STEPS + 1):
        angle = math.pi * i / (2 * ARC_STEPS)
        c, s = math.cos(angle), math.sin(angle)
        r, z = OUTER_RADIUS * c, EQUATOR_Z + DOME_RISE * s
        normal_length = math.hypot(DOME_RISE * c, OUTER_RADIUS * s)
        outer_arc.append((r, z))
        inner_arc.append((r - DOME_WALL * DOME_RISE * c / normal_length,
                          z - DOME_WALL * OUTER_RADIUS * s / normal_length))
    dome = lathe("Translucent dome", [(OUTER_RADIUS, SEAM_Z)] + outer_arc +
                 list(reversed(inner_arc)) + [(inner, SEAM_Z)], collection)
    for index in range(DOME_LOCK_COUNT):
        angle = index * 360.0 / DOME_LOCK_COUNT
        entry = rotated_box("Dome bayonet entry slot",
                            (DOME_LOCK_TAB_INNER_RADIUS - 0.10, -DOME_LOCK_SLOT_WIDTH / 2, SEAM_Z - 0.70),
                            (DOME_LOCK_TAB_OUTER_RADIUS + 0.20,
                             DOME_LOCK_SLOT_WIDTH / 2,
                             DOME_LOCK_TAB_Z + DOME_LOCK_TAB_HEIGHT + 0.20),
                            angle, collection)
        boolean(dome, entry, "DIFFERENCE")
        groove = rotated_box("Dome bayonet locking groove",
                             (DOME_LOCK_TAB_INNER_RADIUS - 0.10, -DOME_LOCK_GROOVE_WIDTH / 2,
                              DOME_LOCK_TAB_Z - 0.20),
                             (DOME_LOCK_TAB_OUTER_RADIUS + 0.20,
                              DOME_LOCK_GROOVE_WIDTH / 2,
                              DOME_LOCK_TAB_Z + DOME_LOCK_TAB_HEIGHT + 0.20),
                             angle - DOME_LOCK_ANGLE_DEG / 2,
                             collection)
        boolean(dome, groove, "DIFFERENCE")
    base.data.materials.append(material("Charcoal base", (0.075, 0.09, 0.11)))
    bottom.data.materials.append(base.data.materials[0])
    dome.data.materials.append(material("Diffuser white", (0.84, 0.90, 0.92)))
    for polygon in dome.data.polygons:
        polygon.use_smooth = abs(polygon.normal.z) < 0.9999
    parts = [base, dome, bottom]
    report = {obj.name: validate(obj) for obj in parts}
    report["assembly"] = {"revision": 3, "print_count": 3,
                          "diameter_mm": 2 * OUTER_RADIUS,
                          "height_mm": EQUATOR_Z + DOME_RISE - BOTTOM_Z,
                          "led_seating_height_mm": LED_MOUNT_Z,
                          "led_hole_pitch_mm": LED_HOLE_PITCH,
                          "led_pilot_diameter_mm": 2 * LED_PILOT_RADIUS,
                          "pico_translation_y_mm": PICO_SHIFT_Y,
                          "usb_recess_depth_mm": round(OUTER_RADIUS - port_outer, 2),
                          "service_bottom_radius_mm": service_bottom_radius,
                          "inset_lip_depth_mm": BASE_INSET_DEPTH,
                          "inset_lip_height_mm": round(BASE_FLOOR + 0.05 - FRAME_SKIRT_BOTTOM, 2),
                          "inset_lip_clearance_mm": FRAME_SKIRT_CLEARANCE,
                          "dome_bayonet_count": DOME_LOCK_COUNT,
                          "dome_bayonet_lock_angle_deg": DOME_LOCK_ANGLE_DEG,
                          "dome_bayonet_groove_width_mm": DOME_LOCK_GROOVE_WIDTH,
                          "dome_radial_fit_mm": RADIAL_FIT,
                          "physical_fit_tested": False}
    for obj, name in zip(parts, ("round_frame.stl", "round_dome.stl", "service_bottom.stl")):
        export_stl(obj, output / name)
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    # Export only the generated assembly, never unrelated objects in the open file.
    generated = bpy.data.scenes.new("Round light export")
    generated.collection.children.link(collection)
    generated.unit_settings.system = "METRIC"
    generated.unit_settings.scale_length = 0.001
    generated.unit_settings.length_unit = "MILLIMETERS"
    generated.world = bpy.data.worlds.new("Round light world")
    if args.render:
        preview(generated, collection, parts, output)
    blend_path = output / "round_enclosure.blend"
    bpy.data.libraries.write(str(blend_path), {generated})
    # A library-only .blend opens to an empty startup scene. Finalize in a fresh
    # Blender process so the assembly opens directly, without saving user scenes.
    finalize = "\n".join([
        "import bpy",
        "scene = bpy.data.scenes['Round light export']",
        "bpy.context.window.scene = scene",
        "for other in list(bpy.data.scenes):",
        "    if other != scene: bpy.data.scenes.remove(other)",
        "for obj in list(bpy.data.objects):",
        "    if obj.name not in scene.objects: bpy.data.objects.remove(obj, do_unlink=True)",
        "bpy.ops.object.select_all(action='SELECT')",
        "for area in bpy.context.screen.areas:",
        "    if area.type == 'VIEW_3D':",
        "        area.spaces.active.region_3d.view_distance = 130",
        "        area.spaces.active.region_3d.view_location = (0, 0, 32)",
        "bpy.context.preferences.filepaths.save_version = 0",
        "bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)",
    ])
    subprocess.run([bpy.app.binary_path, "--background", str(blend_path),
                    "--python-exit-code", "1", "--python-expr", finalize], check=True)
    bpy.data.scenes.remove(generated)
    print(json.dumps(report, indent=2))
    print(f"Created round enclosure in {output}")


if __name__ == "__main__":
    main()
