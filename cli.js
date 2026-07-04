#!/usr/bin/env node
/**
 * Morph Worker — Bulk Morph API Key Generator
 * CLI wrapper: Node.js → Python core
 *
 * Usage: morphworker <command> [args]
 *        node cli.js <command> [args]
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const PROJECT_DIR = __dirname;
const PYTHON_CMD = process.platform === 'win32' ? 'python' : 'python3';
const CLI_SCRIPT = path.join(PROJECT_DIR, 'src', 'cli.py');

// Banner
const BANNER = `
╔══════════════════════════════════════════╗
║          🦊 MORPH WORKER v0.1.0          ║
║     Bulk Morph API Key Generator         ║
║            By mmoaa                       ║
╚══════════════════════════════════════════╝
`;

function showHelp() {
  console.log(BANNER);
  console.log(`
Usage: morphworker <command> [options]

Commands:
  install             Install Python deps + Playwright Chromium
  run <count>         Create N accounts
    --resume          Skip already-created accounts
    --no-headless     Show browser window
    --concurrency N   Parallel accounts (default: 1)
    --provider NAME   Email provider: mocasus | gsuite
    --password STR    Custom password for all accounts

  config              Show current config
    --set KEY=VAL     Set config value (comma-separated)
    --reset           Reset to defaults

  export              Export results
    --format FMT      json | csv | env (default: json)

Examples:
  morphworker install
  morphworker run 10
  morphworker run 5 --resume --concurrency 2
  morphworker config --set mocasus_api_key=YOUR_KEY
  morphworker export --format csv
`);
}

function runInstall() {
  const { execSync } = require('child_process');
  console.log('📦 Installing Python dependencies...');
  try {
    execSync(`"${PYTHON_CMD}" -m pip install -r "${path.join(PROJECT_DIR, 'requirements.txt')}"`, {
      stdio: 'inherit', cwd: PROJECT_DIR
    });
    console.log('✅ Python deps installed.');
  } catch (e) {
    console.error('⚠️ pip install failed. Run manually: pip install -r requirements.txt');
  }

  console.log('🎭 Installing Playwright Chromium...');
  try {
    // Prefer python module (works without npx)
    execSync(`"${PYTHON_CMD}" -m playwright install chromium`, { stdio: 'inherit', cwd: PROJECT_DIR });
    console.log('✅ Playwright Chromium installed.');
  } catch (e) {
    console.error('⚠️ playwright install failed. Run manually: python3 -m playwright install chromium');
  }

  console.log('\n🦊 Morph Worker ready! Run: morphworker run 5');
}

function runPython(args) {
  return new Promise((resolve, reject) => {
    const child = spawn(PYTHON_CMD, [CLI_SCRIPT, ...args], {
      cwd: PROJECT_DIR,
      stdio: 'inherit',
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    });

    child.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`Python exited with code ${code}`));
    });

    child.on('error', (err) => {
      reject(new Error(`Failed to start Python: ${err.message}`));
    });
  });
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    showHelp();
    process.exit(0);
  }

  // Handle install command (no Python needed)
  if (args[0] === 'install') {
    runInstall();
    process.exit(0);
  }

  // Forward all args to Python CLI
  try {
    await runPython(args);
  } catch (err) {
    console.error(`❌ ${err.message}`);
    process.exit(1);
  }
}

main();
