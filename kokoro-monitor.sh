#!/bin/bash
# Monitor Kokoro logs for CUDA errors and auto-restart

CONTAINER_NAME="kokoro-tts"
LOG_CHECK_INTERVAL=10
ERROR_PATTERNS="CUDA error|Failed to load voice tensor|unknown error"

while true; do
    # Check last 50 lines of logs for CUDA errors
    if docker logs "$CONTAINER_NAME" --tail 50 2>&1 | grep -E "$ERROR_PATTERNS" | grep -v "ago" >/dev/null; then
        # Check if error is recent (within last minute)
        LAST_ERROR=$(docker logs "$CONTAINER_NAME" --tail 50 2>&1 | grep -E "$ERROR_PATTERNS" | tail -1)
        
        # Get timestamp of container logs
        CURRENT_TIME=$(date +%s)
        CONTAINER_START=$(docker inspect -f '{{.State.StartedAt}}' "$CONTAINER_NAME" | xargs date +%s -d)
        UPTIME=$((CURRENT_TIME - CONTAINER_START))
        
        # Only restart if container has been up for more than 60 seconds (avoid restart loops)
        if [ $UPTIME -gt 60 ]; then
            echo "$(date): CUDA error detected, restarting $CONTAINER_NAME..."
            docker restart "$CONTAINER_NAME"
            
            # Wait for container to fully start
            sleep 20
            
            # Log the restart
            echo "$(date): $CONTAINER_NAME restarted due to CUDA error" >> /home/echo/projects/kokoro/recovery.log
        fi
    fi
    
    sleep $LOG_CHECK_INTERVAL
done