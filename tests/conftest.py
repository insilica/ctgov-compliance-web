import sys
import os
from pathlib import Path

# Ensure project root is in sys.path so 'web' can be imported
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
    
# Print debug info
print(f"Project root: {ROOT}")
print(f"sys.path: {sys.path}")
