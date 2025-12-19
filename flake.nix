{
  description = "fork_agent - Plataforma agéntica para bifurcación de terminales";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        fork-agent = pkgs.python3Packages.buildPythonApplication {
          pname = "fork-agent";
          version = "1.0.0";
          
          src = ./.;
          
          propagatedBuildInputs = with pkgs; [
            python3
          ];
          
          # No hay requirements.txt complejos, usa stdlib
          format = "other";
          
          installPhase = ''
            mkdir -p $out/bin
            mkdir -p $out/share/fork_agent
            
            # Copiar script principal
            cp .claude/skills/fork_terminal/tools/fork_terminal.py $out/bin/fork-terminal
            chmod +x $out/bin/fork-terminal
            
            # Copiar configuración y cookbooks
            cp -r .claude $out/share/fork_agent/
            
            # Crear wrapper con variables de entorno
            cat > $out/bin/fork-terminal-wrapper <<EOF
            #!/usr/bin/env bash
            export FORK_AGENT_HOME="$out/share/fork_agent"
            export FORK_AGENT_PROMPTS="\$FORK_AGENT_HOME/.claude/skills/fork_terminal/prompts"
            export FORK_AGENT_COOKBOOK="\$FORK_AGENT_HOME/.claude/skills/fork_terminal/cookbook"
            exec ${pkgs.python3}/bin/python3 $out/bin/fork-terminal "\$@"
            EOF
            chmod +x $out/bin/fork-terminal-wrapper
          '';
          
          meta = with pkgs.lib; {
            description = "Plataforma agéntica para bifurcación de terminales con soporte multi-agente";
            homepage = "https://github.com/indydevdan/fork_agent";
            license = licenses.mit;
            platforms = platforms.darwin ++ platforms.linux;
          };
        };
        
      in {
        packages.default = fork-agent;
        packages.fork-agent = fork-agent;
        
        apps.default = {
          type = "app";
          program = "${fork-agent}/bin/fork-terminal-wrapper";
        };
        
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python3
            fish
            tmux
            # Agentes opcionales (descomentar si están disponibles en nixpkgs)
            # gemini-cli
            # claude
          ];
          
          shellHook = ''
            export FORK_AGENT_HOME="${self}/."
            export FORK_AGENT_PROMPTS="$FORK_AGENT_HOME/.claude/skills/fork_terminal/prompts"
            echo "🚀 fork_agent dev environment loaded"
            echo "Run: python3 .claude/skills/fork_terminal/tools/fork_terminal.py"
          '';
        };
      }
    );
}
