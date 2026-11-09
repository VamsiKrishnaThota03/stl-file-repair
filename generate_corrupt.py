"""Generate test meshes: a watertight unit cube and a copy with holes.

    python generate_corrupt.py              # valid_cube.stl + corrupted_cube.stl (one side removed)
    python generate_corrupt.py --holes 3    # remove the +X, +Y and +Z sides (one larger hole)
    python generate_corrupt.py --random-bytes 0.01 --seed 1
                                            # instead randomise 1% of the bytes (the file may not load)
"""
import argparse

import numpy as np
import trimesh


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--valid", default="valid_cube.stl", help="watertight cube output")
    parser.add_argument("--output", default="corrupted_cube.stl", help="corrupted cube output")
    parser.add_argument("--holes", type=int, default=1, choices=(1, 2, 3),
                        help="number of cube sides (2 triangles each) to remove")
    parser.add_argument("--random-bytes", type=float, metavar="FRACTION",
                        help="randomise this fraction of the bytes instead of removing faces")
    parser.add_argument("--seed", type=int, default=None, help="random seed for --random-bytes")
    args = parser.parse_args(argv)

    cube = trimesh.creation.box(extents=(1, 1, 1))
    cube.export(args.valid)
    print(f"Valid STL saved as {args.valid}.")

    if args.random_bytes:
        rng = np.random.default_rng(args.seed)
        with open(args.valid, "rb") as fh:
            data = bytearray(fh.read())
        # Skip the 80-byte header and triangle count so the file is more likely to stay parseable.
        for index in rng.integers(84, len(data), int(len(data) * args.random_bytes)):
            data[index] = int(rng.integers(0, 256))
        with open(args.output, "wb") as fh:
            fh.write(data)
        print(f"Byte-corrupted STL saved as {args.output}.")
        return 0

    # Remove the +X, +Y and/or +Z sides (each side is two triangles).
    normals = np.round(cube.face_normals).astype(int)
    keep = np.ones(len(cube.faces), dtype=bool)
    for axis in range(args.holes):
        direction = np.zeros(3, dtype=int)
        direction[axis] = 1
        keep &= ~np.all(normals == direction, axis=1)
    holed = trimesh.Trimesh(cube.vertices, cube.faces[keep], process=False)
    holed.export(args.output)
    print(f"STL with {args.holes} missing side(s) saved as {args.output} "
          f"({len(holed.faces)} of {len(cube.faces)} faces).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
