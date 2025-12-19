#!/usr/bin/env python3
"""Generate summary from agent checkout log."""

import sys
from pathlib import Path
from datetime import datetime

def parse_yaml_log(log_file: str):
    """Parse YAML-like log file manually."""
    agents = []
    current_agent = {}
    
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            
            if line == '---':
                if current_agent:
                    agents.append(current_agent)
                current_agent = {}
            elif ':' in line:
                key, value = line.split(':', 1)
                value = value.strip().strip('"')
                
                if key == 'timestamp':
                    current_agent['timestamp'] = value
                elif key == 'agent_id':
                    current_agent['agent_id'] = value
                elif key == 'agent_name':
                    current_agent['agent_name'] = value
                elif key == 'status':
                    current_agent['status'] = value
                elif key == 'duration_seconds':
                    current_agent['duration_seconds'] = int(value) if value.isdigit() else 0
                elif key == 'report_path':
                    current_agent['report_path'] = value if value != 'null' else None
                elif key == 'summary':
                    current_agent['summary'] = value
    
    if current_agent:
        agents.append(current_agent)
    
    return agents

def generate_summary(log_file: str):
    """Generate summary from agent checkout log."""
    
    if not Path(log_file).exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    agents = parse_yaml_log(log_file)
    
    if not agents:
        print("📝 No agents have checked out yet.")
        return
    
    total = len(agents)
    successful = sum(1 for a in agents if a.get('status') == 'SUCCESS')
    failed = total - successful
    
    print("=" * 60)
    print("AGENT CHECKOUT SUMMARY")
    print("=" * 60)
    print(f"\nTotal Agents: {total}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {(successful/total)*100:.1f}%")
    
    if agents:
        total_duration = sum(a.get('duration_seconds', 0) for a in agents)
        avg_duration = total_duration / total
        print(f"⏱️  Average Duration: {avg_duration:.1f}s")
    
    print("\n" + "-" * 60)
    print("AGENT DETAILS")
    print("-" * 60)
    
    for agent in agents:
        status_icon = "✅" if agent.get('status') == 'SUCCESS' else "❌"
        agent_id = agent.get('agent_id', 'Unknown')
        agent_name = agent.get('agent_name', 'Unknown')
        duration = agent.get('duration_seconds', 0)
        
        print(f"\n{status_icon} {agent_id}: {agent_name}")
        print(f"   ⏱️  Duration: {duration}s")
        
        if agent.get('report_path'):
            print(f"   📄 Report: {agent['report_path']}")
        
        if agent.get('summary'):
            print(f"   💬 Summary: {agent['summary']}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    log_file = sys.argv[1] if len(sys.argv) > 1 else ".claude/logs/agent_checkout.log"
    generate_summary(log_file)
