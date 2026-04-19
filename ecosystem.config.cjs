const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env') });

const PROJECT_ROOT = __dirname;
const VENV_PYTHON = process.env.PYTHON_INTERPRETER || path.join(PROJECT_ROOT, '.venv', 'bin', 'python');
const OPENCODE_BIN = process.env.OPENCODE_BIN || path.join(process.env.HOME || '', '.opencode', 'bin', 'opencode');
const OPENCODE_BIN_DIR = path.dirname(OPENCODE_BIN);
const PROCESS_PATH = process.env.PATH || '';
const API_ENV = {
  PYTHONUNBUFFERED: '1',
  PYTHONPATH: PROJECT_ROOT,
  API_HOST: '0.0.0.0',
  API_PORT: '8080',
  API_DEBUG: 'false',
  API_KEY: process.env.API_KEY || '',
  OPENCODE_BIN,
  PATH: `${OPENCODE_BIN_DIR}:${PROCESS_PATH}`
};

module.exports = {
  apps: [
    // Fork Agent CLI (main command)
    {
      name: 'fork-agent-cli',
      script: './src/interfaces/cli/main.py',
      interpreter: VENV_PYTHON,
      args: '--help',
      cwd: PROJECT_ROOT,
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: PROJECT_ROOT
      },
      autorestart: false,
      watch: false
    },
    // Fork Agent API (FastAPI)
    {
      name: 'fork-agent-api',
      script: './src/interfaces/api/main.py',
      interpreter: VENV_PYTHON,
      cwd: PROJECT_ROOT,
      env: API_ENV,
      autorestart: true,
      watch: false,
      instances: 1,
      exec_mode: 'fork'
    }
  ]
};
