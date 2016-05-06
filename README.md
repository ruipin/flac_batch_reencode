# FLAC Batch Re-encode

**By Rui Pinheiro**

A Python 2.7 script for batch re-encoding many *.flac files recursively. This is useful to make sure that your whole FLAC library is using the latest version of the FLAC encoder, with maximum compression.

Files can be skipped if the encoder matches a user-defined vendor string (i.e., they were already encoded using the latest FLAC encoder).

## Usage

Place `metaflac` and `flac` in your search path, and then run:

`reencode.py [-h] [-f <folder>] [-m <mask>] [--check-vendor] [-v [--vendor-string <vendor>]] [--no-verify] [--flac <flac-path>] [--metaflac <metaflac-path>]`

| Parameter       | Description   |
| :---------------: | ------------- |
| `-h` | `--help` | Shows script description and usage help. |
| `-f <folder>` \ `--folder <folder>`   |    Root folder path for recursive search (default: `.`). |
| `-m <mask>` / `--mask <mask>`     |    File mask (default: `*.flac`). |
| `-v` / `--vendor`   |    Skip file if vendor string matches `<vendor>` (requires `metaflac`). |
| `--vendor-string <vendor>` |    Desired vendor string for `-v` (default: `reference libFLAC 1.3.1 20141125`). |
| `--no-verify`     |    Do not verify output for encoding errors before overwriting original files. Faster, but *in rare cases could result in corrupt files*. |
| `--flac <flac-path>` | Path to the `flac` executable (default: `flac`). |
| `--metaflac <metaflac-path>` | Path to the `metaflac` executable (only required if using `-v`, default: `metaflac`). |

## Implementation

This script first creates a list of all the files inside `<folder>`. If using `-v`, `metaflac --show-vendor-tag` is compared with `<vendor>` in order to detect which files are using different FLAC encoder versions.
Once the list is created, each file will be re-encoded using `<flac-path> -s -V <file> --force --best`. This uses the best possible compression level, and overwrites the input file after the output is verified.

**Note:** The use of `-V` in the FLAC encoding parameters means that encoding takes longer, but any problems during encoding will be detected before the original file is overwritten. If you do not mind the (low) risk, and want the whole re-encoding process to complete faster, use `--no-verify` to ommit the `-V`.

## License

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.