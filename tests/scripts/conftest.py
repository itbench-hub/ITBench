import sys
from pathlib import Path

# Make scripts/ importable by all tests in this directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
