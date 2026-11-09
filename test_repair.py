"""Run with: python -m unittest -v"""
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import trimesh

import repair_stl

QUIET = io.StringIO


def cube_without(*normals):
    cube = trimesh.creation.box(extents=(1, 1, 1))
    keep = np.ones(len(cube.faces), dtype=bool)
    for normal in normals:
        keep &= ~np.all(np.round(cube.face_normals) == normal, axis=1)
    return trimesh.Trimesh(cube.vertices, cube.faces[keep], process=False)


class RepairTests(unittest.TestCase):
    def repair(self, mesh):
        with redirect_stdout(QUIET()):
            return repair_stl.repair_mesh_manually(mesh)

    def test_single_hole_is_closed(self):
        mesh = cube_without((1, 0, 0))
        with redirect_stdout(QUIET()):
            self.assertEqual(len(repair_stl.find_open_edges(mesh)), 4)
        repaired, changed = self.repair(mesh)
        self.assertTrue(changed)
        self.assertTrue(repaired.is_watertight)
        self.assertTrue(repaired.is_winding_consistent)
        self.assertAlmostEqual(abs(repaired.volume), 1.0, places=6)

    def test_adjacent_holes_become_one_loop(self):
        mesh = cube_without((1, 0, 0), (0, 1, 0), (0, 0, 1))
        with redirect_stdout(QUIET()):
            loops = repair_stl.find_boundary_loops(mesh)
        self.assertEqual(len(loops), 1)
        repaired, _ = self.repair(mesh)
        self.assertTrue(repaired.is_watertight)

    def test_triangular_hole_gets_one_face(self):
        mesh = trimesh.creation.icosphere(subdivisions=1)
        mesh = trimesh.Trimesh(mesh.vertices, mesh.faces[1:], process=False)
        with redirect_stdout(QUIET()):
            added = repair_stl.fill_holes(mesh)
        self.assertEqual(added, 1)
        self.assertTrue(mesh.is_watertight)

    def test_watertight_mesh_is_untouched(self):
        mesh = trimesh.creation.box()
        faces = mesh.faces.copy()
        _, changed = self.repair(mesh)
        self.assertFalse(changed)
        np.testing.assert_array_equal(mesh.faces, faces)

    def test_sample_file_and_cli(self):
        sample = Path(__file__).with_name("corrupted_stl_file.stl")
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(QUIET()):
            out = Path(tmp) / "out.stl"
            code = repair_stl.main([str(sample), "-o", str(out), "--no-view", "--plot-dir", tmp])
            self.assertEqual(code, 0)
            self.assertTrue(trimesh.load(out, force="mesh").is_watertight)
            self.assertTrue((Path(tmp) / "before.png").exists())
            self.assertTrue((Path(tmp) / "after.png").exists())

    def test_missing_file(self):
        with redirect_stdout(QUIET()):
            self.assertEqual(repair_stl.main(["does-not-exist.stl", "--no-view"]), 1)


if __name__ == "__main__":
    unittest.main()
