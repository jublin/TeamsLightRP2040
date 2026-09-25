# Round enclosure, revision 2

**56 mm diameter × 49.5 mm high.** This revision mounts the electronics directly
in a purpose-built round enclosure. The original square shells and matrix tray
are not installed. The original STL files remain unmodified.

![New internal structure](output_v2/exploded.png)

## What changed

- The LED board screws directly to four integrated, sloped brackets. Its original
  19 × 19 mm hole pattern and 2.529 mm pilot diameter are retained. The seats are
  at Z=25 mm, compared with Z=37.3 mm in the first pass.
- The Pico mounts on a removable circular bottom. Only the small board/pin
  retention features are extracted from the original STL. The tall square walls
  and original enclosure's four corner insert towers are discarded.
- The Pico is moved 5.5 mm toward the perimeter. Its original USB opening envelope
  is reproduced in a flat face, with a 3.5 mm exterior recess instead of 13 mm.
  This face moves with the service bottom through an open-bottom slot in the
  frame, so the projecting USB socket does not trap the board during removal.
- Wiring passes through the open center. There is no matrix tray or restrictive
  center hole, and the electronics can be accessed from underneath.
- The bottom uses three peripheral M3 insert bosses. These hold the new enclosure
  together; they do not obstruct the Pico or LED mounting pattern.

The three new prints are a **round frame**, **service bottom with Pico cradle**,
and **translucent dome**. The old printed holders and square diffuser are replaced.

## Generate and check

Tested in Blender 5.2.2, using only its bundled Python modules. From the repository
root:

```sh
blender --background --python-exit-code 1 --python 3DModels/blender/round_dome.py -- --render
blender --background 3DModels/blender/output_v2/round_enclosure.blend --python-exit-code 1 --python 3DModels/blender/check_fit.py
```

You can also open the saved script in Blender's Text Editor and choose **Run
Script**. Keep it in this folder so the original STLs can be found. Command-line
options `--models /path/to/3DModels` and `--output /path/to/destination` override
the defaults. `--render` adds the three previews.

Current output is in **`output_v2/`**:

- `round_enclosure.blend`: assembled model, opening directly to the assembly.
- `round_frame.stl`, `service_bottom.stl`, `round_dome.stl`: separate printable parts.
- `assembled.png`, `interior.png`, `exploded.png`: shape previews.
- `validation.json`: closed-mesh checks, volumes, and dimensions.
- `fit_checks.json`: collision, retention, insertion-clearance and mounting checks.

The `output/` folder contains the superseded first-pass model for comparison.
Do not mix its printed parts with revision 2. Each STL is independently placed
on Z=0 for slicing; use the Blender file to inspect the assembled positions.

Running the generator replaces only its named collection and generated files.
It sets the active scene units to millimetres. Other existing objects remain;
the saved assembly excludes them.

## Hardware and assembly

Reuse the RP2040 Zero, 4×4 LED matrix, JST connectors, wires, and short LED screws.
Three of the original M3×4 mm threaded inserts fit the new service-bottom bosses.
The bottom closure is designed for **three M3×6 mm button-head screws**, with
head diameter at most 6.4 mm and head height at most 1.8 mm. Check your existing
screws; obtain matching screws if necessary.

1. Install the three inserts from the frame's underside, flush with the boss
   faces. The sockets are 4.1 mm diameter, following the original insert bore.
2. Fit the Pico into the service bottom's retention features, in the same
   chip-down orientation as the original. Its USB port faces the nearby edge.
3. Connect the JST wiring while the bottom is accessible. Bring the bottom up
   into the frame, align the USB aperture, and fasten the three bottom screws.
4. Lay the LED board onto the four seats and use the original short self-tapping
   screws. Pilot depth is 4 mm; limit screw projection below the PCB to 3 mm.
   Arrange the wire slack in the open center, away from the screw seats.
5. Slide the dome over the frame's 4 mm locating lip. It rests at Z=16 mm.

The dome is a removable slip cover with 0.30 mm radial clearance. It has no
positive latch; lift the device by the base. The bottom, frame and dome can each
be removed for servicing.

## Printing and fit limits

Print the frame and bottom in opaque material and the 1.6 mm thick dome in
translucent material. The bracket undersides slope at 45 degrees. Review the
dome roof support/bridging in your slicer. The previews show geometry, not tested
optical diffusion. A small joint test print can help tune `RADIAL_FIT`.

The fit checks verify that the three printed pieces do not overlap, the retained
Pico cradle has not lost material, and the four LED seats and pilot depths are
correct. They also check a sampled service-bottom insertion path with the PCB,
projecting USB socket and JST allowances, and assumed electronics
clearance envelopes: 18.3 × 23.5 × 1.59 mm for the Pico PCB above the supports,
17 × 8 × 9 mm for JST connector space, and 35 × 35 × 4 mm above the LED seats.
These envelopes are inferred allowances, **not exact component CAD models**.
Cable molding, solder joints, connector placement, printer tolerances, and the
full assembly motion still need a physical fit test. No physical print test has
been performed.

![Round enclosure](output_v2/assembled.png)
