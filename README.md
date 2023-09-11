# Dynamic Window Capture for OBS

This python script allows capturing of windows in OBS that have a dynamic title. This is useful for capturing WhatsApp or other programs where you want to capture a window based on a regular expression.

This script is cross platform and should work on Windows, Mac and Linux.

## Installation

OBS requires you to install a compatible version of Python.

The following dependencies are needed:
- [PyWinCtl](https://github.com/Kalmat/PyWinCtl)
- ObsPython (Comes bundled with OBS-Studio)

To install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Create a scene and a Window Capture source. The program/window this captures is not important at this point.
2. Add the script to OBS.
3. Choose the name of the source you wish to update.
4. Specify an executable (case insensitive) - e.g. "whatsapp.exe".
5. Provide a regular expression for the window title - e.g. ".*video call".

Whenever a window changes, a check is done to update the capture settings of the configured capture source.

## License
[MIT](https://choosealicense.com/licenses/mit/)