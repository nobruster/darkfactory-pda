const ENV_ALLOWLIST = [
  "HOME",
  "LANG",
  "LC_ALL",
  "LC_CTYPE",
  "PATH",
  "SHELL",
  "TEMP",
  "TMP",
  "TMPDIR",
  "TZ",
];

export function createReadOnlyEnvironment(
  baseEnvironment,
  { cvgHome, projectRoot },
) {
  const environment = {};
  for (const name of ENV_ALLOWLIST) {
    const value = baseEnvironment?.[name];
    if (typeof value === "string" && value.length > 0) {
      environment[name] = value;
    }
  }

  environment.CVG_HOME = cvgHome;
  environment.CVG_PROJECT_ROOT = projectRoot;
  environment.CVG_COLOR = "0";
  environment.GIT_OPTIONAL_LOCKS = "0";
  environment.NO_COLOR = "1";

  return environment;
}

const SECRET_ASSIGNMENT =
  /((?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|passwd|private[_-]?key|secret|token)\s*["']?\s*[:=]\s*["']?)([^\s"',;}\]]+)/gi;
const BEARER_TOKEN = /(authorization\s*:\s*bearer\s+)[^\s"']+/gi;
const PRIVATE_KEY_BLOCK =
  /-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----/g;
const KNOWN_TOKEN =
  /\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})\b/g;

export function redactSensitiveTextWithReport(value) {
  const original = String(value);
  const content = original
    .replace(PRIVATE_KEY_BLOCK, "[REDACTED PRIVATE KEY]")
    .replace(SECRET_ASSIGNMENT, "$1[REDACTED]")
    .replace(BEARER_TOKEN, "$1[REDACTED]")
    .replace(KNOWN_TOKEN, "[REDACTED]");

  return {
    content,
    redacted: content !== original,
  };
}

export function redactSensitiveText(value) {
  return redactSensitiveTextWithReport(value).content;
}

export function publicError(code, message) {
  return {
    ok: false,
    error: {
      code,
      message,
    },
  };
}
