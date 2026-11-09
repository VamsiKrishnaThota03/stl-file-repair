# STL File Repair

A small Python tool that finds holes (open edges) in an STL mesh, visualises them in 3D, patches them with new faces and exports the result.

![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB?logo=python&logoColor=white)
![trimesh](https://img.shields.io/badge/trimesh-mesh%20processing-informational)
![Matplotlib](https://img.shields.io/badge/Matplotlib-3D%20plots-11557c)

## Overview

STL files exported from CAD tools or scanners are often not watertight: some triangle edges belong to only one face, leaving gaps in the surface. This project loads an STL file with [`trimesh`](https://trimesh.org/), detects those open edges, highlights them in a Matplotlib 3D view, adds faces to close the gaps, re-orients normals and saves a repaired copy.

A helper script is included to generate a valid test cube and a deliberately corrupted copy of it.

## Features

- **File picker**: choose the input `.stl` through a Tkinter file dialog
- **Open-edge detection**: counts how many faces use each edge; edges used exactly once are reported as open
- **3D visualisation**: Matplotlib view with open edges drawn in red and faces adjacent to them shaded yellow (the window closes on its own after about 15 seconds)
- **Hole filling**: for every open edge, new triangles are added that connect the edge to the other mesh vertices, then `trimesh`'s `fix_normals()` is applied
- **Before/after views**: shows the corrupted mesh, then the repaired mesh
- **Export**: writes the repaired mesh to `repaired_cube.stl`
- **Test data generator**: `generate_corrupt.py` writes a unit cube (`valid_cube.stl`) and a copy with about 1% of its bytes randomised (`corrupted_cube.stl`)

> **Note:** the hole-filling strategy is a simple brute-force approach. It closes open edges, but on larger meshes it can add many extra (and overlapping) faces. It is meant for experimenting on small models, not as a production mesh-repair pipeline.

## Tech stack

- Python 3.7+
- [trimesh](https://github.com/mikedh/trimesh): mesh loading, normal fixing and export
- NumPy: face array manipulation
- Matplotlib (`mplot3d`): 3D visualisation
- Tkinter: file selection dialog (ships with most Python installs)

## Project structure

```
stl-file-repair/
├── repair_stl.py            # Main tool: detect, visualise, repair and export
├── generate_corrupt.py      # Builds a valid cube STL and a byte-corrupted copy
├── valid_cube.stl           # Sample: watertight unit cube
├── corrupted_stl_file.stl   # Sample: ASCII cube with a missing face ("cube_with_hole")
├── repaired.stl             # Sample output
└── repaired_cube.stl        # Sample output (default output file name)
```

## Getting started

### Prerequisites

- Python 3.7 or later
- A desktop environment (the tool opens a file dialog and plot windows)

### Install

```bash
git clone https://github.com/VamsiKrishnaThota03/stl-file-repair.git
cd stl-file-repair

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install trimesh numpy matplotlib
```

### Run

```bash
python repair_stl.py
```

1. Pick an STL file in the dialog (for example `corrupted_stl_file.stl`).
2. The terminal prints the number of open edges found.
3. If the mesh has holes, a "Corrupted Mesh" view opens with the open edges highlighted.
4. The mesh is repaired and a "Repaired Mesh" view opens.
5. The result is saved as `repaired_cube.stl` in the current directory. Change `output_file_path` in `repair_stl.py` to use another name.

If the mesh is already watertight, the tool says so and exits without writing a file.

### Generate test files

```bash
python generate_corrupt.py
# -> valid_cube.stl and corrupted_cube.stl
```

## Contact

Thota Vamsi Krishna — [GitHub](https://github.com/VamsiKrishnaThota03)
