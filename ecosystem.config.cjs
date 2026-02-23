module.exports = {
  apps: [
    // Fork Agent CLI (main command)
    {
      name: 'fork-agent-cli',
      script: './src/interfaces/cli/main.py',
      interpreter: 'python3',
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
      interpreter: 'python3',
      cwd: '/Users/felipe_gonzalez/Developer/tmux_fork',
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: '/Users/felipe_gonzalez/Developer/tmux_fork',
        API_HOST: '0.0.0.0',
        API_PORT: '8080',
        API_DEBUG: 'false',
        API_KEY: ''
      },
      autorestart: true,
      watch: false,
      instances: 1,
      exec_mode: 'fork'
    }
  ]
}
