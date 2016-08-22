Tested with Python 2.7.11

## Required modules (tested ver.):
  * pyqt 4.11.4
  * numpy 1.10.4

## Usage
1. Launch from align_app.py
2. Choose run directory. If valid run directory is specified, map file will be auto-detected. Otherwise, manually specify map file.
3. Switch between Print and Wafer tabs to choose alignment type. Sample numbers are not required for wafer alignment. All other stage parameters are required.
4. Filter parameters are optional and auto-filled with defaults when a map file is loaded. Filters are applied in order:
  1. Filter codes & omit channels, use comma or space separated lists.
  2. Crop area by map coordinate limits.
  3. Skip samples, columns, rows. (at.% option WIP)
  4. Manually specify sample list and/or trim start and end.
5. Use "Preview output" button to dry run. Messages will be in the log.
6. Use "Generate stage and sample list" to save output to run directory.

## License
See the [LICENSE](LICENSE.md) file for license rights and limitations (MIT).
