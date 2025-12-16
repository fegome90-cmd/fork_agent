# Prompt

## History

Esta es la historia de la conversacion entre el usuario y el agente.

``` yaml
- history:
    - user_prompt_summary: User set up the environment and requested to fork a terminal using gemini-cli with the fast model to analyze the history file.
      agent_response_summary: Agent analyzed the project structure and prepared to fork the terminal.
    - user_prompt: "fork nueva terminal, gemini-cli, fast model, summary history \" analiza el \"@/workspaces/fork_agent/.claude/skills/fork_terminal/prompts/fork_summary_user_prompts.md \" y haz un resumen en .claude/docs\""
      agent_response: "I will fork a new terminal with gemini-cli using the fast model."
    - user_prompt: "fork 2 nuevas terminales, gemini-cli, fast model, summary history: terminal A \"Analiza skills.md y haz un resumen de las herramientas en docs\". TErminal B \"analiza prime.md y haz un resumen en docs\""
      agent_response: "I will fork two new terminals with gemini-cli using the fast model, one for analyzing skills.md and another for prime.md."
```

## Next User Request

Terminal A: Analiza skills.md y haz un resumen de las herramientas en docs.
Terminal B: analiza prime.md y haz un resumen en docs.

```