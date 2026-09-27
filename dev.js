const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const isWin = process.platform === 'win32';
const venvPy = isWin 
  ? path.join(__dirname, '.venv', 'Scripts', 'python.exe')
  : path.join(__dirname, '.venv', 'bin', 'python');

const pythonExe = fs.existsSync(venvPy) ? venvPy : (isWin ? 'python' : 'python3');

const isTest = process.argv.includes('test');
const args = isTest ? ['verify_all.py'] : ['run_server.py'];

// Resolve configured port
let port = 8000;
try {
  const envPath = path.join(__dirname, '.env');
  if (fs.existsSync(envPath)) {
    const envContent = fs.readFileSync(envPath, 'utf8');
    const match = envContent.match(/^PORT\s*=\s*(\d+)/m);
    if (match) port = parseInt(match[1], 10);
  }
} catch (e) {}

if (process.env.PORT) {
  port = parseInt(process.env.PORT, 10);
}

// Automatically free port if occupied by a stale process
function freePortIfBusy(targetPort) {
  try {
    if (isWin) {
      const out = execSync('netstat -ano -p tcp', { stdio: ['pipe', 'pipe', 'ignore'] }).toString();
      const lines = out.split('\n');
      for (const line of lines) {
        if (line.includes(`:${targetPort}`) && line.includes('LISTENING')) {
          const parts = line.trim().split(/\s+/);
          const pid = parts[parts.length - 1];
          if (pid && pid !== '0' && pid !== String(process.pid)) {
            console.log(`[dev] Port ${targetPort} is occupied by PID ${pid}. Stopping stale process...`);
            execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
            // Brief wait for socket release
            const end = Date.now() + 300;
            while (Date.now() < end) {}
          }
        }
      }
    }
  } catch (e) {
    // Port check or taskkill error ignored
  }
}

if (!isTest) {
  freePortIfBusy(port);
  if (!process.argv.includes('--no-reload')) {
    args.push('--reload');
  }
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
