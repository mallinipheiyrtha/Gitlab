"""Test that bjt_bias.bjt does not import Flask."""
import subprocess
import sys

code = "import sys; import bjt_bias.bjt; sys.stdout.write('flask' in sys.modules)"
output = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True)
print('Flask in modules:', output.stdout.strip())
assert output.stdout.strip() == 'False'
print('Independence test: PASSED')