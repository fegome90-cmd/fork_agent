# Prompt - Agent 2: Audit

## History

```yaml
history:
  - user_prompt_summary: "User requested to read and understand the prime.md command file"
    agent_response_summary: "Agent followed the prime.md workflow, reading all documentation files and provided comprehensive analysis of fork_agent platform"
    capa_modificada: "Documentation"
    impacto_contrato: "None"
    siguiente_paso_tecnico: "Execute fork terminal operations"
  
  - user_prompt_summary: "Fork terminal with Codex to analyze zellij implementation"
    agent_response_summary: "Agent executed fork with Codex CLI, which generated detailed analysis report identifying critical bugs in zellij implementation"
    capa_modificada: "Application"
    impacto_contrato: "None"
    siguiente_paso_tecnico: "Review fork agent results and implement fixes"
  
  - user_prompt_summary: "Create 2 sequential fork agents: one to implement fixes, one to audit"
    agent_response_summary: "Agent 1 launched to implement fixes. Agent 2 being prepared for audit"
    capa_modificada: "Application"
    impacto_contrato: "Implementation fixes zellij session creation bug"
    siguiente_paso_tecnico: "Agent 2 audits Agent 1's implementation"
```

## Task: Audit Zellij Implementation (Agent 2)

```json
{
  "task": "audit_zellij_implementation",
  "context": {
    "original_analysis": "/Users/felipe_gonzalez/Developer/fork_agent-main/docs/zellij_implementation_analysis.md",
    "implementation_report": "/Users/felipe_gonzalez/Developer/fork_agent-main/docs/zellij_fix_implementation.md",
    "modified_file": "/Users/felipe_gonzalez/Developer/fork_agent-main/.claude/skills/fork_terminal/tools/fork_terminal.py",
    "lines_to_audit": "76-95",
    "original_bugs": [
      "zellij run -d -n <session_name> does not create named sessions",
      "Flag -n names pane, not session",
      "zellij attach <session_name> will always fail",
      "read -p can hang in detached panes"
    ]
  },
  "chain_of_thought": {
    "step_1_review_requirements": {
      "action": "Read original analysis report to understand what needed to be fixed",
      "file": "/Users/felipe_gonzalez/Developer/fork_agent-main/docs/zellij_implementation_analysis.md",
      "extract": [
        "All critical bugs identified",
        "All 5 recommendations",
        "Expected behavior"
      ],
      "output": "Checklist of requirements"
    },
    "step_2_review_implementation": {
      "action": "Read Agent 1's implementation report",
      "file": "/Users/felipe_gonzalez/Developer/fork_agent-main/docs/zellij_fix_implementation.md",
      "understand": [
        "What changes were made",
        "Why changes were made",
        "How bugs were addressed"
      ],
      "output": "Understanding of implementation approach"
    },
    "step_3_inspect_code": {
      "action": "Read modified fork_terminal.py lines 76-95",
      "file": "/Users/felipe_gonzalez/Developer/fork_agent-main/.claude/skills/fork_terminal/tools/fork_terminal.py",
      "verify": [
        "Session creation is explicit (uses --session flag)",
        "Session name is correctly set",
        "No blocking read -p command",
        "Return message matches actual behavior",
        "Syntax is correct for zellij"
      ],
      "output": "Code inspection results"
    },
    "step_4_validate_fixes": {
      "action": "Validate each bug was properly fixed",
      "checks": {
        "bug_1_session_creation": "Verify session is created with proper name",
        "bug_2_flag_usage": "Verify --session is used instead of -n for session naming",
        "bug_3_attach_works": "Verify attach command will work with created session",
        "bug_4_no_hang": "Verify no read -p or other blocking commands",
        "recommendation_1": "Session is created explicitly",
        "recommendation_2": "Pane vs session concepts are separated",
        "recommendation_3": "Return message is accurate",
        "recommendation_4": "No read -p present",
        "recommendation_5": "Semantics match tmux behavior"
      },
      "output": "Validation results per bug/recommendation"
    },
    "step_5_test_scenarios": {
      "action": "Consider edge cases and test scenarios",
      "scenarios": [
        "What if zellij is not installed?",
        "What if session name already exists?",
        "What if command fails?",
        "Is error handling adequate?",
        "Are there version compatibility issues?"
      ],
      "output": "Edge case analysis"
    },
    "step_6_final_verdict": {
      "action": "Provide final audit verdict",
      "assess": [
        "Are all bugs fixed? (Yes/No for each)",
        "Are all recommendations implemented? (Yes/No for each)",
        "Is code quality acceptable?",
        "Are there remaining risks?",
        "Overall: PASS or FAIL"
      ],
      "output": "Final verdict with justification"
    },
    "step_7_document": {
      "action": "Create comprehensive audit report",
      "location": "/Users/felipe_gonzalez/Developer/fork_agent-main/docs/zellij_audit_report.md",
      "include": [
        "Audit methodology (CoT steps followed)",
        "Requirements checklist with status",
        "Code review findings",
        "Bug fix validation (each bug)",
        "Edge cases identified",
        "Final verdict (PASS/FAIL)",
        "Recommendations for further improvement (if any)"
      ],
      "output": "Complete audit documentation"
    }
  },
  "deliverables": {
    "audit_report": "/Users/felipe_gonzalez/Developer/fork_agent-main/docs/zellij_audit_report.md",
    "verdict": "PASS or FAIL with detailed justification"
  },
  "audit_criteria": {
    "critical": "All 4 critical bugs must be fixed for PASS",
    "recommendations": "At least 4 of 5 recommendations must be implemented for PASS",
    "code_quality": "Code must be readable, maintainable, and follow Python best practices",
    "correctness": "Implementation must be syntactically and semantically correct"
  }
}
```

## Execution Instructions

1. Wait for Agent 1 to complete (check for implementation report)
2. Read all required documents thoroughly
3. Follow Chain of Thought steps sequentially
4. Validate each bug fix against original analysis
5. Provide clear PASS/FAIL verdict with justification
6. Create comprehensive audit report in docs/
