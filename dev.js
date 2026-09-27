const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const isWin = process.platform === 'win32';
const venvPy = isWin 
  ? path.join(__dirname, '.venv', 'Scripts', 'python.exe')
  : path.join(__dirname, '.venv', 'bin', 'python');

const pythonExe = fs.existsSync(venvPy) ? venvPy : (isWin ? 'python' : 'python3');

const isTest = process.argv.includes('test');
const args = isTest ? ['verify_all.py'] : ['run_server.py'];

if (!isTest && !process.argv.includes('--no-reload')) {
  args.push('--reload');
}

const child = spawn(pythonExe, args, {
  stdio: 'inherit',
  shell: false
});

child.on('error', (err) => {
  console.error('[dev] Failed to execute Python command:', err.message);
  if (!fs.existsSync(venvPy)) {
    console.error('[dev] Notice: Virtual environment .venv was not found. Run run.bat to set it up automatically.');
  }
  process.exit(1);
});

child.on('exit', (code) => {
  process.exit(code || 0);
});
