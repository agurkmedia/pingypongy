const { spawn } = require('child_process');
const path = require('path');

const backendPath = path.join(__dirname, 'app', 'backend');

const backend = spawn('python', ['main.py'], {
  cwd: backendPath,
  stdio: 'inherit'
});

backend.on('close', (code) => {
  console.log(`Backend process exited with code ${code}`);
});