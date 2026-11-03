import sys
import unittest
from pathlib import Path
root=Path(__file__).parent
sys.path.insert(0,str(root/'vendor'))
suite=unittest.defaultTestLoader.discover(str(root/'tests'))
result=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
