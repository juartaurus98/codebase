#!/usr/bin/env node
/**
 * data-guard.js — Claude Code PreToolUse Hook
 *
 * Blocks AI from reading, writing, or executing commands involving
 * sensitive files (credentials, secrets, private keys, .env, etc.)
 *
 * Install: copy to your project and register in .claude/settings.json
 * (see hooks/settings.json for registration template)
 *
 * Exit codes:
 *   0 = allow the tool call
 *   2 = block the tool call (Claude Code interprets this as a hard block)
 */

const readline = require('readline');

// ── Sensitive file patterns ────────────────────────────────────────────────

const SENSITIVE_PATH_PATTERNS = [
  // Environment files
  /^\.env$/i,
  /^\.env\./i,
  /\.env$/i,

  // Secret/credential files
  /secret/i,
  /credential/i,
  /password/i,
  /passwd/i,
  /private[_-]?key/i,
  /api[_-]?key/i,
  /access[_-]?token/i,
  /auth[_-]?token/i,

  // Crypto keys and certificates
  /\.key$/i,
  /\.pem$/i,
  /\.p12$/i,
  /\.pfx$/i,
  /\.jks$/i,
  /\.keystore$/i,

  // Framework-specific prod configs
  /application-(prod|production|staging)\.(yml|yaml|properties)$/i,
  /appsettings\.(Production|Staging)\.json$/i,
  /database\.yml$/i,
  /config\/master\.key$/i,
  /storage\/oauth-private\.key$/i,

  // Secret directories
  /^secrets\//i,
  /\/secrets\//i,
  /^\.secrets\//i,
];

const SENSITIVE_BASH_PATTERNS = [
  /\bprintenv\b/i,
  /\benv\b.*\|\s*(grep|awk|sed).*secret/i,
  /cat\s+\.env/i,
  /docker\s+inspect/i,
  /kubectl\s+get\s+secret.*-o\s+yaml/i,
];

// ── Helpers ────────────────────────────────────────────────────────────────

function isSensitivePath(filePath) {
  if (!filePath) return false;
  const normalized = filePath.replace(/\\/g, '/');
  return SENSITIVE_PATH_PATTERNS.some(pattern => pattern.test(normalized));
}

function isSensitiveCommand(command) {
  if (!command) return false;
  return SENSITIVE_BASH_PATTERNS.some(pattern => pattern.test(command));
}

function block(reason) {
  console.error(`\n🔒 DATA GUARD — BLOCKED\n${reason}\n`);
  console.error('If you need configuration values, describe what you need');
  console.error('without sharing actual secrets. Use placeholder values in generated code.\n');
  process.exit(2);
}

// ── Main ───────────────────────────────────────────────────────────────────

let rawInput = '';

process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { rawInput += chunk; });
process.stdin.on('end', () => {
  let input;
  try {
    input = JSON.parse(rawInput);
  } catch {
    // Cannot parse input — allow (fail open, not fail closed)
    process.exit(0);
  }

  const toolName  = input.tool_name  || '';
  const toolInput = input.tool_input || {};

  // ── Read tool ─────────────────────────────────────────────────────────
  if (toolName === 'Read') {
    const filePath = toolInput.file_path || '';
    if (isSensitivePath(filePath)) {
      block(`Attempted to READ sensitive file: ${filePath}`);
    }
  }

  // ── Write tool ────────────────────────────────────────────────────────
  if (toolName === 'Write') {
    const filePath = toolInput.file_path || '';
    if (isSensitivePath(filePath)) {
      block(`Attempted to WRITE to sensitive file: ${filePath}`);
    }
  }

  // ── Edit tool ─────────────────────────────────────────────────────────
  if (toolName === 'Edit') {
    const filePath = toolInput.file_path || '';
    if (isSensitivePath(filePath)) {
      block(`Attempted to EDIT sensitive file: ${filePath}`);
    }
  }

  // ── Bash tool ─────────────────────────────────────────────────────────
  if (toolName === 'Bash') {
    const command = toolInput.command || '';
    if (isSensitiveCommand(command)) {
      block(`Attempted to execute sensitive command: ${command}`);
    }
    // Also check if the command references a sensitive file path
    if (isSensitivePath(command)) {
      block(`Bash command references a sensitive file path: ${command}`);
    }
  }

  // Allow all other tool calls
  process.exit(0);
});
