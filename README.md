# RayStudio Gaussian Splat PLY Converter

A lightweight Python utility for converting selected **3DMakerpro RayStudio** Gaussian Splatting PLY exports into a PLY layout accepted by tools such as **SuperSplat**.

This utility was developed by **Pohjois-Suomen Rakennusklusteri ry (Northern Finland Construction Cluster Association)** in connection with the **SmartBuiltNorth (SBNorth)** project. The work explores practical 3D capture, data processing and interoperability workflows for the built environment.

> **Independent community utility.** This project is not an official 3DMakerpro, RayStudio or SuperSplat product and is not endorsed by those vendors.

## Why this converter exists

In tested RayStudio Gaussian PLY exports, each splat contains **38 float32 properties**, including three `f_dc` values and **21 `f_rest` values** (`f_rest_0` through `f_rest_20`). A commonly used degree-2 Gaussian Splatting PLY layout instead contains three `f_dc` values and **24 `f_rest` values** (`f_rest_0` through `f_rest_23`). Some tools expect that layout.

The converter adapts this specific export structure so it can be opened in compatible third-party tools. This is a **compatibility workaround**, not a claim that the original RayStudio model or its rendering is incorrect.

## What it does

- Reads a binary little-endian Gaussian PLY file with the expected 38-float property layout.
- Adds **three zero-valued SH coefficients**, padding each of the three color-channel groups from seven to eight `f_rest` values (21 → 24 total).
- Preserves the splat count and the existing coefficient values.
- Applies a **−90° rotation around the X axis** to splat positions, normals and orientation quaternions, converting `(x, y, z)` to `(x, z, −y)`.
- Writes a new PLY file, leaving the original input untouched.
- Supports Windows file selection and command-line input/output paths.
- Validates the expected input structure and output size.

## Requirements

- Python 3.10 or newer (recommended)
- Python standard library only; no `pip install` required
- For graphical file selection: a Python installation with Tkinter and a desktop environment

## Usage

From the project directory, open a terminal and run:

```powershell
python -u .\converter.py
```

A file-selection dialog opens. Select the **original RayStudio Gaussian PLY** file, not an already converted file.

Alternatively, provide file paths:

```powershell
python -u .\converter.py "C:\path\input.ply" "C:\path\output.ply"
```

If no output path is specified, the script creates a new PLY alongside the source using its configured output suffix. The terminal shows conversion progress.

Open the resulting PLY in SuperSplat or another compatible viewer and inspect its appearance and orientation. The converter does not require the SuperSplat source repository, Node.js or a local web server; those are only needed if you choose to run SuperSplat locally.

## Supported format and limitations

| Property | Expected input | Converted output |
| --- | ---: | ---: |
| Binary format | Little-endian PLY | Little-endian PLY |
| Properties per splat | 38 × float32 | 41 × float32 |
| `f_dc` values | 3 | 3 |
| `f_rest` values | 21 | 24 |
| SH values in total | 24 | 27 |
| Bytes per splat | 152 | 164 |

**Important limitations:**

1. **No missing data is reconstructed.** The additional SH coefficients are zeros; the original source does not provide those values.
2. **SH directional coefficients are not rotated.** Although splat positions, normals and orientation quaternions are rotated, view-dependent colors may change after conversion.
3. **The axis rotation is specific to the tested workflow.** Do not assume every RayStudio export needs the same −90° X rotation.
4. **Only the specified input layout is supported.** Other PLY variants, including ordinary point clouds, may not be compatible.
5. **Visual compatibility is not a guarantee of measurement accuracy.** Check coordinate systems, scale, geometry and alignment independently before using the output in engineering workflows.

## Project context

**SmartBuiltNorth (SBNorth)** investigates digital workflows and the use of emerging technologies in the construction and built-environment sector. Within this work, Pohjois-Suomen Rakennusklusteri ry is evaluating how scanner outputs, point clouds, Gaussian Splatting models and related data can move between software environments and support downstream use cases.

This repository shares one small, reproducible interoperability utility from that experimentation. It is not a complete Eagle/RayStudio processing pipeline, and it does not provide georeferencing, SLAM correction or reconstruction of missing measurement data.

## License and disclaimer

Copyright © 2026 **Pohjois-Suomen Rakennusklusteri ry**.

Released under the **MIT License**; see [LICENSE](LICENSE). The software is provided **“AS IS”, WITHOUT WARRANTY OF ANY KIND**. To the extent permitted by applicable law, the copyright holders and contributors are not liable for claims, damages or other liability arising from use of the software. **Use and validate outputs at your own risk.**

The full license text governs; this README summary does not replace it.

## Acknowledgements

- **3DMakerpro RayStudio** — source of the Gaussian PLY exports used in testing.
- **SuperSplat** — one of the third-party Gaussian Splatting tools used to evaluate interoperability.

Product and project names belong to their respective owners.
