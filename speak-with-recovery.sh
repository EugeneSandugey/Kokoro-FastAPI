#!/bin/bash
# Speak command with CUDA error recovery

MAX_RETRIES=3
RETRY_DELAY=5

speak_with_retry() {
    local text="$1"
    local attempt=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        # Try to speak
        if timeout 30 speak "$text" 2>&1 | tee /tmp/speak_output.log; then
            # Success
            return 0
        else
            # Check if it's a CUDA error
            if grep -q "CUDA error\|Failed to load voice tensor" /tmp/speak_output.log; then
                echo "CUDA error detected, attempt $attempt of $MAX_RETRIES"
                
                if [ $attempt -lt $MAX_RETRIES ]; then
                    echo "Restarting Kokoro container..."
                    docker restart kokoro-tts >/dev/null 2>&1
                    sleep $RETRY_DELAY
                    
                    # Wait for container to be ready
                    for i in {1..10}; do
                        if curl -s http://localhost:8880/health >/dev/null 2>&1; then
                            echo "Kokoro is ready, retrying..."
                            break
                        fi
                        sleep 1
                    done
                fi
            else
                # Non-CUDA error, don't retry
                return 1
            fi
        fi
        
        ((attempt++))
    done
    
    echo "Failed after $MAX_RETRIES attempts"
    return 1
}

# Call the function with all arguments
speak_with_retry "$*"