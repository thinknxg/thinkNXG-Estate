import os
import sys

# make `thinknxg_estate` importable when pytest runs from the repository without a bench
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
