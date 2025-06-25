# test_import.py
try:
    import numpy as np
    print("NumPy imported successfully, version:", np.__version__)
    import pandas as pd
    print("Pandas imported successfully, version:", pd.__version__)
except ImportError as e:
    print("Import error:", e)