require('dotenv').config({ path: '/Users/felipe_gonzalez/Developer/tmux_fork/.env' });

module.exports = {
  apps: [
    // Fork Agent CLI (main command)
    {
      name: 'fork-agent-cli',
      script: './src/interfaces/cli/main.py',
      interpreter: '/Users/felipe_gonzalez/Developer/tmux_fork/.venv/bin/python',
      args: '--help',
      cwd: '/Users/felipe_gonzalez/Developer/tmux_fork',
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: '/Users/felipe_gonzalez/Developer/tmux_fork'
      },
      autorestart: false,
      watch: false
    },
    // Fork Agent API (FastAPI)
    {
      name: 'fork-agent-api',
      script: './src/interfaces/api/main.py',
      interpreter: '/Users/felipe_gonzalez/Developer/tmux_fork/.venv/bin/python',
      cwd: '/Users/felipe_gonzalez/Developer/tmux_fork',
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: '/Users/felipe_gonzalez/Developer/tmux_fork',
        API_HOST: '0.0.0.0',
        API_PORT: '8080',
        API_DEBUG: 'false',
        API_KEY: process.env.API_KEY || '',
        OPENCODE_BIN: '/Users/felipe_gonzalez/.opencode/bin/opencode',
        PATH: `${process.env.PATH || ''}:/Users/felipe_gonzalez/.opencode/bin`
      },
      autorestart: true,
      watch: false,
      instances: 1,
      exec_mode: 'fork'
    }
  ]
}
