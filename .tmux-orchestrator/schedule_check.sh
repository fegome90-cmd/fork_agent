#!/bin/bash
# Dynamic scheduler with note for next check
# Usage: ./schedule_check.sh <minutes> "<note>" [target_window]

PROJECT_ROOT="/home/user/fork_agent"
MINUTES=${1:-30}
NOTE=${2:-"Standard check-in"}
TARGET=${3:-"orchestrator:0"}

# Create a note file for the next check
NOTE_FILE="$PROJECT_ROOT/.tmux-orchestrator/next_check_note.txt"
echo "=== Next Check Note ($(date)) ===" > "$NOTE_FILE"
echo "Scheduled for: $MINUTES minutes" >> "$NOTE_FILE"
echo "Target window: $TARGET" >> "$NOTE_FILE"
echo "" >> "$NOTE_FILE"
echo "$NOTE" >> "$NOTE_FILE"

echo "Scheduling check in $MINUTES minutes with note: $NOTE"

# Calculate the exact time when the check will run
CURRENT_TIME=$(date +"%H:%M:%S")
RUN_TIME=$(date -d "+${MINUTES} minutes" +"%H:%M:%S" 2>/dev/null || date -v+${MINUTES}M +"%H:%M:%S" 2>/dev/null)

# Calculate seconds
SECONDS=$((MINUTES * 60))

# Schedule the check using nohup for detached process
nohup bash -c "sleep $SECONDS && tmux send-keys -t $TARGET 'Time for orchestrator check! Read $NOTE_FILE for instructions.' && sleep 1 && tmux send-keys -t $TARGET Enter" > /dev/null 2>&1 &

SCHEDULE_PID=$!

echo "Scheduled successfully - process detached (PID: $SCHEDULE_PID)"
echo "SCHEDULED TO RUN AT: $RUN_TIME (in $MINUTES minutes from $CURRENT_TIME)"
