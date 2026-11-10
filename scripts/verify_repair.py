"""End-to-end check that the repair actually repairs.

Asserting the CLI exits 0 and writes a file would pass even if nothing was
fixed. This compares the mesh before and after: the input must start
non-watertight, the output must end watertight, and faces must have been added.

Usage:
    python scripts/verify_repair.py corrupted_stl_file.stl /tmp/repaired.stl
"""

import sys

import trimesh


def main(argv):
    if len(argv) != 3:
        sys.exit(f"usage: {argv[0]} <input.stl> <repaired.stl>")

    source, repaired_path = argv[1], argv[2]
    before = trimesh.load(source)
    after = trimesh.load(repaired_path)

    print(f"before: watertight={before.is_watertight}, faces={len(before.faces)}")
    print(f"after:  watertight={after.is_watertight}, faces={len(after.faces)}")

    if before.is_watertight:
        sys.exit(
            f"{source} is already watertight, so this check proves nothing — "
            "the fixture has drifted"
        )
    if not after.is_watertight:
        sys.exit("repaired mesh is still not watertight")
    if len(after.faces) <= len(before.faces):
        sys.exit("no faces were added, so no hole was filled")

    print("repair verified")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
