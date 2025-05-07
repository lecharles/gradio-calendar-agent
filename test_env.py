import sys
print("Python version:", sys.version)
print("\nPython path:")
for path in sys.path:
    print(path)

print("\nTrying to import required packages:")
try:
    import gradio
    print("✓ gradio", gradio.__version__)
except ImportError as e:
    print("✗ gradio:", e)

try:
    import openai
    print("✓ openai", openai.__version__)
except ImportError as e:
    print("✗ openai:", e)

try:
    from google.oauth2.credentials import Credentials
    print("✓ google.oauth2.credentials")
except ImportError as e:
    print("✗ google.oauth2.credentials:", e) 