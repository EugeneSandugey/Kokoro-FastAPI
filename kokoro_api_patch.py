#!/usr/bin/env python3
"""
Minimal CUDA recovery patch for Kokoro TTS API
This file should be placed in the container and imported before the main app
"""
import torch
import gc
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def cuda_recovery_decorator(func):
    """Decorator that adds CUDA error recovery to any function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e)
                if "CUDA error" in error_msg or "unknown error" in error_msg or "Failed to load voice tensor" in error_msg:
                    logger.error(f"CUDA error on attempt {attempt + 1}/{max_retries}: {error_msg}")
                    
                    if attempt < max_retries - 1:
                        # Clear CUDA cache
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                            torch.cuda.synchronize()
                            gc.collect()
                        
                        # Wait before retry
                        time.sleep(2 * (attempt + 1))  # Exponential backoff
                        logger.info("Retrying after CUDA cache clear...")
                        continue
                
                # Either non-CUDA error or max retries reached
                raise
        
        return None  # Should never reach here
    
    return wrapper

def patch_kokoro_api():
    """
    Patch the Kokoro API to add CUDA recovery
    This should be called early in the startup process
    """
    try:
        # Try to patch the main model loading and generation functions
        import sys
        
        # Common function names that might use CUDA
        cuda_functions = [
            'generate', 'forward', 'load_voice', 'load_model',
            'synthesize', 'process', 'infer', '_generate'
        ]
        
        patched_count = 0
        
        for module_name, module in list(sys.modules.items()):
            if module and ('kokoro' in module_name or 'tts' in module_name):
                try:
                    for attr_name in dir(module):
                        if any(fn in attr_name.lower() for fn in cuda_functions):
                            attr = getattr(module, attr_name, None)
                            if callable(attr) and not attr_name.startswith('_'):
                                wrapped = cuda_recovery_decorator(attr)
                                setattr(module, attr_name, wrapped)
                                patched_count += 1
                                logger.info(f"Patched {module_name}.{attr_name} with CUDA recovery")
                except Exception as e:
                    logger.debug(f"Could not patch {module_name}: {e}")
        
        logger.info(f"Successfully patched {patched_count} functions with CUDA recovery")
        
        # Also set better CUDA memory management
        if torch.cuda.is_available():
            # Reduce memory fragmentation
            torch.cuda.set_per_process_memory_fraction(0.9)  # Use up to 90% of VRAM
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            
    except Exception as e:
        logger.error(f"Error during Kokoro API patching: {e}")

# Auto-patch on import
patch_kokoro_api()