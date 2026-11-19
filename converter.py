"""RayStudio Gaussian PLY -> SuperSplat PLY.

- Pads 21 f_rest properties to 24 (per-channel zero padding).
- Converts Z-up to Y-up with -90 degrees about X:
  (x, y, z) -> (x, z, -y).
- Applies the same world rotation to Gaussian orientation quaternions.

Important: SH directional coefficients are padded, not rotated. This preserves the
original coefficients but can affect view-dependent color after axis rotation.
"""

import argparse
import math
import struct
import sys
from pathlib import Path
from tkinter import Tk, filedialog

OLD_STRUCT = struct.Struct('<38f')
NEW_STRUCT = struct.Struct('<41f')
ROOT2_INV = math.sqrt(0.5)

EXPECTED = (
    ['x', 'y', 'z', 'nx', 'ny', 'nz']
    + [f'f_dc_{i}' for i in range(3)]
    + [f'f_rest_{i}' for i in range(21)]
    + ['opacity']
    + [f'scale_{i}' for i in range(3)]
    + [f'rot_{i}' for i in range(4)]
)


def choose_file():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    try:
        return filedialog.askopenfilename(
            title='Valitse RayStudion Gaussian PLY',
            filetypes=[('PLY files', '*.ply'), ('All files', '*.*')],
        )
    finally:
        root.destroy()


def read_header(file):
    lines = []
    for _ in range(1000):
        line = file.readline()
        if not line:
            raise ValueError('PLY-otsake paattyi kesken')
        try:
            s = line.decode('ascii').rstrip('\r\n')
        except UnicodeDecodeError as exc:
            raise ValueError('PLY-otsake ei ole ASCII') from exc
        lines.append(s)
        if s == 'end_header':
            return lines, file.tell()
    raise ValueError('PLY-otsake on poikkeuksellisen pitka')


def validate_header(lines, file_size, header_size):
    if not lines or lines[0] != 'ply':
        raise ValueError('Ei PLY-tiedosto')
    if 'format binary_little_endian 1.0' not in lines:
        raise ValueError('Vain binary_little_endian 1.0 on tuettu')
    vertices = [s for s in lines if s.startswith('element vertex ')]
    if len(vertices) != 1:
        raise ValueError('Vertex-maara puuttuu tai on moniselitteinen')
    count = int(vertices[0].split()[2])
    other_elements = [s for s in lines if s.startswith('element ') and not s.startswith('element vertex ')]
    if other_elements:
        raise ValueError(f'Ylimaaraisia PLY-elementteja: {other_elements}')
    properties = [s for s in lines if s.startswith('property ')]
    if properties != [f'property float {name}' for name in EXPECTED]:
        raise ValueError('PLY:n kentat eivat vastaa RayStudion odotettua 38 float -rakennetta')
    expected_size = header_size + count * OLD_STRUCT.size
    if file_size != expected_size:
        raise ValueError(f'Tiedostokoko ei tasmaa: {file_size} vs {expected_size}')
    return count


def convert_vertex(data):
    v = OLD_STRUCT.unpack(data)
    x, y, z = v[0:3]
    nx, ny, nz = v[3:6]

    # Graphdeco PLY uses rot_0..rot_3 = quaternion (w, x, y, z).
    qw, qx, qy, qz = v[34:38]
    # Left-multiply q by X-axis rotation of -90 degrees.
    # q_axis = (cos(-pi/4), sin(-pi/4), 0, 0)
    c = ROOT2_INV
    s = -ROOT2_INV
    new_q = (
        c * qw - s * qx,
        c * qx + s * qw,
        c * qy - s * qz,
        c * qz + s * qy,
    )

    # RayStudio has 7 SH-rest coefficients per color channel.
    # Standard degree 2 has 8 per channel; pad the missing one with zero.
    rest = v[9:30]
    new_rest = (
        rest[0:7] + (0.0,)
        + rest[7:14] + (0.0,)
        + rest[14:21] + (0.0,)
    )
    new_v = (
        (x, z, -y)
        + (nx, nz, -ny)
        + v[6:9]
        + new_rest
        + v[30:34]
        + new_q
    )
    return NEW_STRUCT.pack(*new_v)


def main():
    parser = argparse.ArgumentParser(description='RayStudio Gaussian PLY -> SuperSplat (SH + X -90 deg)')
    parser.add_argument('input', nargs='?', help='Lahtotiedosto (muuten avataan valintaikkuna)')
    parser.add_argument('output', nargs='?', help='Tulostiedosto')
    args = parser.parse_args()

    chosen = args.input or choose_file()
    if not chosen:
        print('Valinta peruutettu.')
        return 0
    src = Path(chosen).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    dst = (Path(args.output).expanduser().resolve() if args.output else
           src.with_name(src.stem + '-SuperSplat-Yup.ply'))
    if src == dst:
        raise ValueError('Lahto- ja tulostiedosto eivat saa olla samat')
    if dst.exists():
        raise FileExistsError(f'Tulostiedosto on jo olemassa: {dst}')

    print(f'Input:  {src}', flush=True)
    print(f'Output: {dst}', flush=True)
    with src.open('rb') as infile:
        lines, header_size = read_header(infile)
        count = validate_header(lines, src.stat().st_size, header_size)
        new_header = []
        for line in lines:
            new_header.append(line)
            if line == 'property float f_rest_20':
                new_header.extend(f'property float f_rest_{i}' for i in range(21, 24))
        header_bytes = ('\n'.join(new_header) + '\n').encode('ascii')
        print(f'Splats: {count:,}; f_rest 21 -> 24; X rotation: -90 deg', flush=True)
        try:
            with dst.open('xb') as outfile:
                outfile.write(header_bytes)
                for i in range(count):
                    data = infile.read(OLD_STRUCT.size)
                    if len(data) != OLD_STRUCT.size:
                        raise EOFError(f'Kesken kohdassa {i:,}')
                    outfile.write(convert_vertex(data))
                    if (i + 1) % 100_000 == 0 or i + 1 == count:
                        print(f'\r{i + 1:,}/{count:,} ({100 * (i + 1) / count:.1f}%)',
                              end='', flush=True)
            expected = len(header_bytes) + count * NEW_STRUCT.size
            if dst.stat().st_size != expected:
                raise ValueError('Tulostiedoston koko ei tasmaa')
        except Exception:
            dst.unlink(missing_ok=True)
            raise
    print(f'\nDONE: {dst}', flush=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
