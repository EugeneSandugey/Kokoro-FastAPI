#!/usr/bin/env python3
"""
CUDA Recovery Wrapper for Kokoro TTS
Intercepts CUDA errors and automatically recovers
"""
import torch
import gc
import traceback
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class CUDARecovery:
    def __init__(self):
        self.error_count = 0
        self.last_error_time = 0
        self.recovery_threshold = 3  # errors within time window
        self.time_window = 60  # seconds
        
    def clear_cuda_cache(self):
        """Force clear CUDA cache and reset context"""
        try:
            if torch.cuda.is_available():
                # Clear cache
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                
                # Force garbage collection
                gc.collect()
                
                # Reset CUDA context
                torch.cuda.reset_peak_memory_stats()
                
                logger.info("CUDA cache cleared successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to clear CUDA cache: {e}")
            return False
    
    def recover_from_cuda_error(self):
        """Attempt to recover from CUDA error"""
        logger.warning("Attempting CUDA recovery...")
        
        # Step 1: Clear CUDA cache
        self.clear_cuda_cache()
        
        # Step 2: Wait a moment
        time.sleep(2)
        
        # Step 3: Test CUDA
        try:
            if torch.cuda.is_available():
                # Simple test operation
                test_tensor = torch.zeros(1).cuda()
                del test_tensor
                torch.cuda.synchronize()
                logger.info("CUDA recovery successful")
                return True
        except Exception as e:
            logger.error(f"CUDA recovery failed: {e}")
            
        return False
    
    def cuda_safe_wrapper(self, func):
        """Decorator to wrap functions with CUDA error recovery"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    return func(*args, **kwargs)
                except (torch.cuda.CudaError, RuntimeError) as e:
                    if "CUDA" in str(e) or "unknown error" in str(e):
                        retry_count += 1
                        logger.error(f"CUDA error detected (attempt {retry_count}/{max_retries}): {e}")
                        
                        # Track error frequency
                        current_time = time.time()
                        if current_time - self.last_error_time < self.time_window:
                            self.error_count += 1
                        else:
                            self.error_count = 1
                        self.last_error_time = current_time
                        
                        # Attempt recovery
                        if self.recover_from_cuda_error():
                            logger.info("Retrying after successful recovery...")
                            time.sleep(1)
                            continue
                        else:
                            if retry_count < max_retries:
                                logger.warning(f"Recovery failed, waiting longer before retry...")
                                time.sleep(5)
                    else:
                        # Non-CUDA error, don't retry
                        raise
                except Exception as e:
                    # Non-CUDA error
                    logger.error(f"Non-CUDA error: {e}")
                    raise
            
            # If we get here, all retries failed
            raise RuntimeError(f"Failed after {max_retries} CUDA recovery attempts")
        
        return wrapper

# Global instance
cuda_recovery = CUDARecovery()

# Monkey-patch function to inject into Kokoro
def patch_kokoro_model():
    """Patch Kokoro model to add CUDA recovery"""
    try:
        import sys
        # Find Kokoro modules
        for module_name, module in sys.modules.items():
            if 'kokoro' in module_name and hasattr(module, 'generate') or hasattr(module, 'forward'):
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and ('generate' in attr_name or 'forward' in attr_name):
                        # Wrap with CUDA recovery
                        wrapped = cuda_recovery.cuda_safe_wrapper(attr)
                        setattr(module, attr_name, wrapped)
                        logger.info(f"Patched {module_name}.{attr_name} with CUDA recovery")
    except Exception as e:
        logger.error(f"Failed to patch Kokoro: {e}")

if __name__ == "__main__":
    # This would be imported and called in the main Kokoro startup
    logging.basicConfig(level=logging.INFO)
    patch_kokoro_model()