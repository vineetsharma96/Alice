// Convenience entry point only. All world state remains in the native application.
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const windows = process.platform === 'win32';
const executable = path.join(root, 'dist', 'UnderworldLab.exe');
const python = path.join(root, '.venv', windows ? 'Scripts/python.exe' : 'bin/python');
const packaged = windows && fs.existsSync(executable) && process.env.UNDERWORLD_SOURCE !== '1';
if (!packaged && !fs.existsSync(python)) {
  console.error('Run the existing run.cmd or bash run.sh launcher to set up Underworld first.');
  process.exit(2);
}
const args = process.argv.slice(2);
if (process.env.PORT && !args.includes('--port')) args.push('--port', process.env.PORT);
const env = { ...process.env };
const sourceBuild = path.join(root, 'build', 'living-d');
if (!packaged && !env.UNDERWORLD_BUILD && fs.existsSync(sourceBuild)) env.UNDERWORLD_BUILD = sourceBuild;
const child = spawn(packaged ? executable : python,
  packaged ? args : ['-m', 'underworld.app', ...args],
  { cwd: root, stdio: 'inherit', env });
child.on('error', error => { console.error(error.message); process.exitCode = 2; });
child.on('exit', code => { process.exitCode = code === null ? 1 : code; });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
