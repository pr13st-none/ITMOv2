import { spawn } from 'node:child_process';
import { access } from 'node:fs/promises';
import path from 'node:path';

async function pythonCommand(cwd) {
  const local = process.platform === 'win32'
    ? path.join(cwd, '.venv', 'Scripts', 'python.exe')
    : path.join(cwd, '.venv', 'bin', 'python');

  try {
    await access(local);
    return local;
  } catch {
    return process.platform === 'win32' ? 'python' : 'python3';
  }
}

async function runCheck(cwd) {
  const python = await pythonCommand(cwd);
  return new Promise((resolve) => {
    const child = spawn(python, ['check.py'], { cwd, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    const collect = (chunk) => { output += chunk.toString(); };
    child.stdout.on('data', collect);
    child.stderr.on('data', collect);
    child.on('error', (error) => resolve({ code: 1, output: error.message }));
    child.on('close', (code) => resolve({ code: code ?? 1, output }));
  });
}

export const CheckAfterEdit = async ({ directory }) => ({
  'tool.execute.after': async (input, output) => {
    if (!['write', 'edit', 'apply_patch'].includes(input.tool)) return;

    const result = await runCheck(directory);
    const status = result.code === 0 ? 'PASS' : 'FAIL';
    const text = `\n\nAutomatic check: ${status}\n${result.output}`;
    output.output = `${output.output ?? ''}${text}`;

  },
});
