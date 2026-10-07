import { spawn } from 'node:child_process';

function runCheck(cwd) {
  return new Promise((resolve) => {
    const child = spawn('bash', ['check.sh'], { cwd, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    const collect = (chunk) => { output += chunk.toString(); };
    child.stdout.on('data', collect);
    child.stderr.on('data', collect);
    child.on('close', (code) => resolve({ code: code ?? 1, output }));
  });
}

export default {
  id: 'practice4.check-after-edit',
  async setup(ctx) {
    await ctx.tool.hook('execute.after', async (event) => {
      if (event.status !== 'completed') return;
      if (!['write', 'edit', 'patch', 'apply_patch'].includes(event.tool)) return;

      const result = await runCheck(ctx.location.directory);
      const text = `\nAutomatic check: ${result.code === 0 ? 'PASS' : 'FAIL'}\n${result.output}`;

      if (typeof event.result?.content === 'string') {
        event.result.content += text;
      }
    });
  },
};
