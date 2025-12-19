{ lib
, python3Packages
, python3
, stdenv
}:

python3Packages.buildPythonApplication {
  pname = "fork-agent";
  version = "1.0.0";
  
  src = ./.;
  
  format = "other";
  
  installPhase = ''
    mkdir -p $out/bin $out/share/fork_agent
    
    # Copiar script principal
    cp .claude/skills/fork_terminal/tools/fork_terminal.py $out/bin/fork-terminal
    chmod +x $out/bin/fork-terminal
    
    # Copiar toda la estructura de configuración
    cp -r .claude $out/share/fork_agent/
    
    # Crear wrapper con variables de entorno
    cat > $out/bin/fork-terminal-wrapper <<'EOF'
#!/usr/bin/env bash
export FORK_AGENT_HOME="$out/share/fork_agent"
export FORK_AGENT_PROMPTS="$FORK_AGENT_HOME/.claude/skills/fork_terminal/prompts"
export FORK_AGENT_COOKBOOK="$FORK_AGENT_HOME/.claude/skills/fork_terminal/cookbook"
exec ${python3}/bin/python3 $out/bin/fork-terminal "$@"
EOF
    chmod +x $out/bin/fork-terminal-wrapper
  '';
  
  meta = with lib; {
    description = "Plataforma agéntica para bifurcación de terminales con soporte multi-agente";
    longDescription = ''
      fork_agent permite bifurcar sesiones de terminal a nuevas ventanas,
      ejecutando comandos CLI o agentes de IA (Gemini CLI, Claude Code, Codex CLI).
      Soporta macOS, Windows y Linux con múltiples estrategias de ejecución.
    '';
    homepage = "https://github.com/indydevdan/fork_agent";
    license = licenses.mit;
    platforms = platforms.darwin ++ platforms.linux;
    maintainers = [ ];
  };
}
