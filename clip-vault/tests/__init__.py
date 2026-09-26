import atexit
import os
import shutil
import tempfile

testHome = tempfile.mkdtemp(prefix="clip-vault-test-")
atexit.register(shutil.rmtree, testHome, True)
os.environ["HOME"] = testHome
