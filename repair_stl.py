"""Find holes (open edges) in an STL mesh, visualise them, close them and export the result.

Usage:
    python repair_stl.py [input.stl] [-o repaired.stl] [--no-view] [--plot-dir DIR]

Without an input path a file dialog is opened (requires Tkinter and a desktop).
"""
import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import trimesh


def load_and_parse_stl(file_path):
    """Load an STL file as a single mesh (duplicate vertices are merged). Returns None on error."""
    try:
        print(f"Loading STL file: {file_path}")
        mesh = trimesh.load(file_path, force="mesh")
    except Exception as exc:  # trimesh raises many different parser errors
        print(f"Error loading STL file: {exc}")
        return None
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        print("Error loading STL file: no triangles found.")
        return None
    print(f"Loaded {len(mesh.vertices)} vertices and {len(mesh.faces)} faces.")
    return mesh


def _undirected_edges(faces):
    faces = np.asarray(faces)
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    return [tuple(sorted(edge)) for edge in edges.tolist()]


def find_open_edges(stl_mesh):
    """Edges used by exactly one face, as sorted (v1, v2) vertex-index tuples."""
    counts = Counter(_undirected_edges(stl_mesh.faces))
    open_edges = [edge for edge, count in counts.items() if count == 1]
    print(f"Number of open edges: {len(open_edges)}")
    return open_edges


def find_boundary_loops(stl_mesh):
    """Group open edges into loops of vertex indices, ordered along each hole.

    Each loop follows the direction the edges have in their existing faces, so the
    patch faces created from it get the opposite (consistent) winding.
    """
    open_set = set(find_open_edges(stl_mesh))
    outgoing = defaultdict(list)  # start vertex -> end vertices of boundary half-edges
    for a, b, c in np.asarray(stl_mesh.faces).tolist():
        for u, v in ((a, b), (b, c), (c, a)):
            if tuple(sorted((u, v))) in open_set:
                outgoing[u].append(v)

    loops = []
    while any(outgoing.values()):
        start = next(v for v, targets in outgoing.items() if targets)
        loop = [start]
        current = start
        while True:
            nxt = outgoing[current].pop()
            if nxt == start:
                break
            if nxt in loop or not outgoing[nxt]:
                # Non-manifold or broken boundary: close what we have.
                if nxt not in loop:
                    loop.append(nxt)
                break
            loop.append(nxt)
            current = nxt
        if len(loop) >= 3:
            loops.append(loop)
    return loops


def fill_holes(stl_mesh):
    """Close every boundary loop with a triangle fan around the loop's centroid.

    Triangular holes are closed with a single face. Returns the number of faces added.
    """
    loops = find_boundary_loops(stl_mesh)
    vertices = np.asarray(stl_mesh.vertices, dtype=float)
    new_vertices = []
    new_faces = []
    for loop in loops:
        if len(loop) == 3:
            a, b, c = loop
            new_faces.append([c, b, a])
            continue
        centre_index = len(vertices) + len(new_vertices)
        new_vertices.append(vertices[loop].mean(axis=0))
        for i, a in enumerate(loop):
            b = loop[(i + 1) % len(loop)]
            new_faces.append([b, a, centre_index])

    if new_faces:
        stl_mesh.vertices = np.vstack([vertices, new_vertices]) if new_vertices else vertices
        stl_mesh.faces = np.vstack([stl_mesh.faces, new_faces])
        stl_mesh.fix_normals()
    print(f"Closed {len(loops)} hole(s) with {len(new_faces)} new face(s).")
    return len(new_faces)


def repair_mesh_manually(stl_mesh):
    """Fill holes and fix normals. Returns (mesh, repaired); repaired is False
    if the mesh was already watertight."""
    print("Starting repair...")
    if not find_open_edges(stl_mesh):
        print("No open edges found. Mesh is already watertight. Skipping repair.")
        return stl_mesh, False
    fill_holes(stl_mesh)
    print(f"Repair completed. Watertight: {stl_mesh.is_watertight}")
    return stl_mesh, True


def display_mesh_with_edges_and_faces(stl_mesh, open_edges, title="Mesh Visualization",
                                      save_path=None, show=True):
    """Plot the mesh with open edges in red and the faces touching them in yellow.

    ``save_path`` writes a PNG; ``show`` opens an interactive window (blocks until closed).
    """
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    vertices = np.asarray(stl_mesh.vertices)
    faces = np.asarray(stl_mesh.faces)
    open_set = set(open_edges)
    problematic = [i for i, face in enumerate(faces.tolist())
                   if any(tuple(sorted(e)) in open_set
                          for e in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])))]

    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(vertices[faces], alpha=0.25, facecolor="#93c5fd",
                                         edgecolor="#1e3a8a", linewidths=0.6))
    if problematic:
        ax.add_collection3d(Poly3DCollection(vertices[faces[problematic]], alpha=0.6,
                                             facecolor="#facc15", edgecolor="#a16207"))
    for v1, v2 in open_edges:
        ax.plot(*zip(vertices[v1], vertices[v2]), color="#dc2626", lw=2.5)

    mins, maxs = vertices.min(axis=0), vertices.max(axis=0)
    span = float((maxs - mins).max()) or 1.0
    centre = (mins + maxs) / 2
    for setter, c in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), centre):
        setter(c - span / 2, c + span / 2)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    status = f"{len(open_edges)} open edge(s)" if open_edges else "watertight"
    ax.set_title(f"{title} - {len(faces)} faces, {status}")

    if save_path:
        fig.savefig(save_path, dpi=100, bbox_inches="tight")
        print(f"Saved plot to {save_path}")
    if show:
        print(f"Showing {title} (close the window to continue)...")
        plt.show()
    plt.close(fig)


def save_repaired_stl(stl_mesh, output_path):
    """Export the mesh. Returns True on success."""
    try:
        print(f"Saving repaired STL file to: {output_path}")
        stl_mesh.export(output_path)
    except Exception as exc:
        print(f"Error saving STL file: {exc}")
        return False
    print("Repaired STL file saved successfully.")
    return True


def pick_file():
    """Ask for an STL file with a Tkinter dialog. Returns None if unavailable or cancelled."""
    try:
        from tkinter import Tk
        from tkinter.filedialog import askopenfilename
        root = Tk()
    except Exception:  # no Tkinter or no display
        print("No file dialog available; pass the STL path as an argument.")
        return None
    root.withdraw()
    path = askopenfilename(filetypes=[("STL files", "*.stl")])
    root.destroy()
    return path or None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Detect and close holes in an STL mesh.")
    parser.add_argument("input", nargs="?", help="STL file to repair (opens a file dialog if omitted)")
    parser.add_argument("-o", "--output", default="repaired_cube.stl",
                        help="where to write the repaired mesh (default: %(default)s)")
    parser.add_argument("--no-view", action="store_true", help="don't open plot windows")
    parser.add_argument("--plot-dir", help="also save before/after plots as PNG files here")
    args = parser.parse_args(argv)

    input_path = args.input or pick_file()
    if not input_path:
        print("No file selected. Exiting...")
        return 1

    mesh = load_and_parse_stl(input_path)
    if mesh is None:
        return 1

    show = not args.no_view
    plot_dir = Path(args.plot_dir) if args.plot_dir else None
    if plot_dir:
        plot_dir.mkdir(parents=True, exist_ok=True)

    open_edges = find_open_edges(mesh)
    if open_edges and (show or plot_dir):
        display_mesh_with_edges_and_faces(mesh, open_edges, title="Corrupted Mesh",
                                          save_path=plot_dir / "before.png" if plot_dir else None,
                                          show=show)

    repaired_mesh, repaired = repair_mesh_manually(mesh)
    if not repaired:
        print("Mesh is already watertight. Nothing to save.")
        return 0

    remaining = find_open_edges(repaired_mesh)
    if show or plot_dir:
        display_mesh_with_edges_and_faces(repaired_mesh, remaining, title="Repaired Mesh",
                                          save_path=plot_dir / "after.png" if plot_dir else None,
                                          show=show)
    return 0 if save_repaired_stl(repaired_mesh, args.output) else 1


if __name__ == "__main__":
    sys.exit(main())
