const { execSync } = require('child_process');
const path = require('path');

const backendPath = path.join(__dirname, 'app', 'backend');

console.log('Installing Python dependencies...');
try {
  execSync(`pip install -r ${path.join(backendPath, 'requirements.txt')}`, { stdio: 'inherit' });
  console.log('Python dependencies installed successfully.');
} catch (error) {
  console.error('Failed to install Python dependencies:', error);
  process.exit(1);
}