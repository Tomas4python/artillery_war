import sys
from pathlib import Path

# Make the ``artillery_war`` package importable without installing it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
