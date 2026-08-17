import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from freenove_protocol import format_move, format_servo

assert format_move(0.0, 200.0, 45.0) == "G0 X0 Y200 Z45"
assert format_servo(0, 90) == "S9 I0 A90"
print("protocol tests passed")
