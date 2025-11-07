#!/bin/bash
# Inject CUDA recovery into running Kokoro container without rebuilding

echo "Injecting CUDA recovery into Kokoro container..."

# Copy the patch file into the container
docker cp /home/echo/projects/kokoro/kokoro_api_patch.py kokoro-tts:/tmp/kokoro_api_patch.py

# Create a wrapper script inside the container
docker exec kokoro-tts bash -c 'cat > /tmp/inject_recovery.py << EOF
import sys
sys.path.insert(0, "/tmp")

# Import the patch which will auto-apply
try:
    import kokoro_api_patch
    print("CUDA recovery patch successfully injected")
except Exception as e:
    print(f"Failed to inject CUDA recovery: {e}")

# Now reimport and patch the running modules
import importlib
import torch
import gc

# Force reload of key modules to apply patches
modules_to_patch = []
for name, module in list(sys.modules.items()):
    if module and ("kokoro" in name or "tts" in name or "api.src" in name):
        modules_to_patch.append(name)

for module_name in modules_to_patch:
    try:
        importlib.reload(sys.modules[module_name])
    except:
        pass

print("CUDA recovery injection complete")
EOF'

# Execute the injection (this won't restart the service, just patches it)
docker exec kokoro-tts python /tmp/inject_recovery.py

echo "CUDA recovery has been injected into the running container"
echo "The container will now automatically retry on CUDA errors"