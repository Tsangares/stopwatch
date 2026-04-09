# Stopwatch

A minimal GTK3 stopwatch application with lap support.

![Python](https://img.shields.io/badge/Python-3-blue) ![GTK](https://img.shields.io/badge/GTK-3.0-green)

## Features

- Start, stop, and reset timer
- Lap tracking with split times
- Best/worst split highlighting (green/red)
- Dark theme UI
- Keyboard shortcuts

## Requirements

- Python 3
- GTK 3 (`gi` / PyGObject)

## Usage

```bash
python stopwatch.py
```

### Keyboard Shortcuts

| Key   | Action          |
|-------|-----------------|
| Space | Start / Stop    |
| L     | Lap (while running) |
| R     | Reset (while stopped) |
| Q     | Quit            |

## License

MIT
