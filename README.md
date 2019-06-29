# FLAC Batch Re-encode

**By Rui Pinheiro**

A Python 3 script for batch parallel re-encoding of many FLAC files. This is useful to make sure that your whole FLAC library is using the latest version of the FLAC encoder, with maximum compression.

## Usage

Place `metaflac` and `flac` in your search path, and then run:

`reencode.py [-h] [-f <folder>] [-m <mask>] [-p <n_parallel>] [-v [--vendor-string <vendor>]] [--no-verify] [--flac <flac-path>] [--metaflac <metaflac-path>]`

| Parameter       | Description   |
| :---------------: | ------------- |
| `-h` | `--help` | Shows script description and usage help. |
| `-f <folder>` \ `--folder <folder>`   |    Root folder path for recursive search (default: `.`). |
| `-m <mask>` / `--mask <mask>`     |    File mask (default: `*.flac`). |
| `-p` / `--parallel` |    Maximum simultaneous encoder processes (default: `max([CPU count]-1,1)`). |
| `--no-verify`     |    Do not verify output for encoding errors before overwriting original files. Faster, but *in rare cases could result in corrupt files*. |
| `--flac <flac-path>` | Path to the `flac` executable (default: `flac`). |

## Implementation

This script first creates a list of all the files inside `<folder>`. If using `-v`, `metaflac --show-vendor-tag <file>` is compared with `<vendor>` in order to detect which files were encoded using different FLAC encoder versions.
Once the list is created, each file is re-encoded using `<flac-path> -s -V <file> --force --best`. This uses the best possible compression level, and overwrites the input file only after the output is verified.

**Note:** The use of `-V` in the FLAC encoding parameters means that encoding takes longer, but any problems during encoding will be detected before the original file is overwritten. If you do not mind the (low) risk of file corruption due to something going wrong during the encoding process, and want it to complete faster, use `--no-verify` to omit the `-V` encoding parameter.

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