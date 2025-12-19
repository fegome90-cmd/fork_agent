#!/bin/bash
# Monitor agent checkout log in real-time

LOG_FILE="${1:-.claude/logs/agent_checkout.log}"
EXPECTED_AGENTS="${2:-5}"

echo "🔍 Monitoring Agent Checkouts"
echo "=============================="
echo "Log file: ${LOG_FILE}"
echo "Expected agents: ${EXPECTED_AGENTS}"
echo ""

# Create log file if it doesn't exist
touch "${LOG_FILE}"

# Watch log file for changes
tail -f "${LOG_FILE}" 2>/dev/null | while read -r line; do
  if [[ $line == "agent_id:"* ]]; then
    AGENT_ID=$(echo "$line" | sed 's/agent_id: "\(.*\)"/\1/')
    echo "📝 Agent ${AGENT_ID} checking out..."
  elif [[ $line == "status:"* ]]; then
    STATUS=$(echo "$line" | sed 's/status: "\(.*\)"/\1/')
    if [[ $STATUS == "SUCCESS" ]]; then
      echo "   ✅ Status: SUCCESS"
    else
      echo "   ❌ Status: FAILURE"
    fi
  elif [[ $line == "duration_seconds:"* ]]; then
    DURATION=$(echo "$line" | sed 's/duration_seconds: //')
    echo "   ⏱️  Duration: ${DURATION}s"
  elif [[ $line == "report_path:"* ]]; then
    REPORT=$(echo "$line" | sed 's/report_path: "\(.*\)"/\1/')
    if [[ $REPORT != "null" ]]; then
      echo "   📄 Report: ${REPORT}"
    fi
    echo ""
    
    # Check if all agents completed
    COMPLETED=$(grep -c "^status:" "${LOG_FILE}" 2>/dev/null || echo "0")
    if [ $COMPLETED -ge $EXPECTED_AGENTS ]; then
      echo ""
      echo "🎉 All ${EXPECTED_AGENTS} agents completed!"
      echo ""
      echo "📊 Summary:"
      SUCCESS=$(grep -c 'status: "SUCCESS"' "${LOG_FILE}" 2>/dev/null || echo "0")
      FAILURE=$(grep -c 'status: "FAILURE"' "${LOG_FILE}" 2>/dev/null || echo "0")
      echo "   ✅ Successful: ${SUCCESS}"
      echo "   ❌ Failed: ${FAILURE}"
      echo "   📈 Success Rate: $(( SUCCESS * 100 / COMPLETED ))%"
      break
    fi
  fi
done
