import { execFile, spawn } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const E2E_LOCK_ROOT = path.join("tmp", "e2e-locks");
const E2E_BIN_ROOT = path.join("tmp", "e2e-bin");

export function isPythonBackendMode() {
  return String(process.env.RAG_BACKEND ?? "").trim().toLowerCase() === "python";
}

export function createRunContext({ repoRoot, tempNamespace }) {
  const runId = `${Date.now()}-${process.pid}-${Math.random().toString(36).slice(2, 8)}`;
  const baseRoot = path.join(repoRoot, "tmp", tempNamespace);
  const tempRoot = path.join(baseRoot, runId);
  const stateFilePath = path.join(tempRoot, "ts-platform-state.json");

  return {
    runId,
    baseRoot,
    tempRoot,
    stateFilePath
  };
}

export async function prepareRunWorkspace({ baseRoot, tempRoot }) {
  await fs.mkdir(baseRoot, { recursive: true });
  await fs.mkdir(tempRoot, { recursive: true });
}

export async function ensureNextBuild({ webRoot, nextCliPath, repoRoot }) {
  const buildIdPath = path.join(webRoot, ".next", "BUILD_ID");
  const forceBuild = process.env.E2E_FORCE_NEXT_BUILD === "1";

  if (!forceBuild && (await exists(buildIdPath))) {
    return;
  }

  const lockPath = path.join(repoRoot, E2E_LOCK_ROOT, "next-build.lock");
  await withFileLock(lockPath, async () => {
    if (!forceBuild && (await exists(buildIdPath))) {
      return;
    }
    await execFileText(process.execPath, [nextCliPath, "build"], { cwd: webRoot });
  });
}

export async function ensureGoRetrievalBinary({ repoRoot }) {
  const isWindows = process.platform === "win32";
  const binaryPath = path.join(repoRoot, E2E_BIN_ROOT, `retrieval-service-e2e${isWindows ? ".exe" : ""}`);
  const sourceRoot = path.join(repoRoot, "go", "retrievalexecutor");
  const forceBuild = process.env.E2E_FORCE_GO_BUILD === "1";

  if (!forceBuild && (await exists(binaryPath))) {
    return binaryPath;
  }

  const lockPath = path.join(repoRoot, E2E_LOCK_ROOT, "go-retrieval-build.lock");
  await withFileLock(lockPath, async () => {
    if (!forceBuild && (await exists(binaryPath))) {
      return;
    }
    await fs.mkdir(path.dirname(binaryPath), { recursive: true });
    await execFileText(resolveGoExecutable(), ["build", "-o", binaryPath, "./cmd/retrieval-service"], { cwd: sourceRoot });
  });

  return binaryPath;
}

export function createSessionHeaders({
  role,
  userId,
  userName,
  tenantId = "tenant_e2e",
  orgId = "org_e2e"
}) {
  return {
    "x-ragent-role": role,
    "x-ragent-user-id": userId,
    "x-ragent-user-name": userName,
    "x-ragent-tenant-id": tenantId,
    "x-ragent-org-id": orgId
  };
}

export function withJsonHeaders(headers = {}) {
  return {
    "Content-Type": "application/json",
    ...headers
  };
}

export function startProcess({ command, args, cwd, env, label, logRoot, shell = false }) {
  const stdoutPath = path.join(logRoot, `${label}.stdout.log`);
  const stderrPath = path.join(logRoot, `${label}.stderr.log`);
  const child = spawn(command, args, {
    cwd,
    env: {
      ...process.env,
      ...env
    },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
    shell
  });

  let stdout = "";
  let stderr = "";
  let stopping = false;

  const flushLogs = async () => {
    await fs.writeFile(stdoutPath, stdout, "utf8");
    await fs.writeFile(stderrPath, stderr, "utf8");
  };

  child.stdout.on("data", (chunk) => {
    stdout += chunk.toString();
    void flushLogs();
  });

  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
    void flushLogs();
  });

  child.on("exit", (code, signal) => {
    if (stopping) {
      return;
    }
    if (code !== null && code !== 0) {
      console.log(`[${label}] exited with code ${code}`);
    }
    if (signal) {
      console.log(`[${label}] exited with signal ${signal}`);
    }
  });

  child.on("error", (error) => {
    console.log(`[${label}] spawn error: ${error?.code ?? "UNKNOWN"} ${error?.message ?? ""}`);
  });

  return {
    label,
    child,
    markStopping: () => {
      stopping = true;
    },
    stdoutPath,
    stderrPath,
    getStdout: () => stdout,
    getStderr: () => stderr
  };
}

export function startPythonBackend({
  repoRoot,
  tempRoot,
  stateFilePath,
  port,
  label = "python-backend",
  env = {}
}) {
  const pythonRoot = path.join(repoRoot, "python");
  const pythonExecutable =
    process.platform === "win32"
      ? path.join(pythonRoot, ".venv", "Scripts", "python.exe")
      : path.join(pythonRoot, ".venv", "bin", "python");
  const sqlitePath = path.join(tempRoot, "python-ingestion.db");

  return startProcess({
    command: pythonExecutable,
    args: ["-m", "uvicorn", "ragent_python.main:app", "--host", "127.0.0.1", "--port", String(port)],
    cwd: repoRoot,
    env: {
      PYTHONPATH: path.join(repoRoot, "python", "src"),
      PYTHON_HOST: "127.0.0.1",
      PYTHON_PORT: String(port),
      PYTHON_PLATFORM_STATE_PATH: stateFilePath,
      PYTHON_INGESTION_BACKEND: "sqlite",
      PYTHON_INGESTION_SQLITE_PATH: sqlitePath,
      ...env
    },
    label,
    logRoot: tempRoot
  });
}

export async function stopProcess(handle) {
  if (!handle || !handle.child || handle.child.exitCode !== null) {
    return;
  }

  if (typeof handle.markStopping === "function") {
    handle.markStopping();
  }

  if (process.platform === "win32" && handle.child.pid) {
    await new Promise((resolve) => {
      const killer = spawn("taskkill.exe", ["/PID", String(handle.child.pid), "/T", "/F"], {
        stdio: "ignore",
        windowsHide: true
      });
      killer.once("exit", resolve);
      killer.once("error", resolve);
    });
    await new Promise((resolve) => {
      if (handle.child.exitCode !== null) {
        resolve();
        return;
      }
      const timer = setTimeout(resolve, 2000);
      handle.child.once("exit", () => {
        clearTimeout(timer);
        resolve();
      });
    });
    return;
  }

  handle.child.kill();
  await new Promise((resolve) => {
    const timer = setTimeout(() => {
      if (handle.child.exitCode === null) {
        handle.child.kill("SIGKILL");
      }
      resolve();
    }, 2000);

    handle.child.once("exit", () => {
      clearTimeout(timer);
      resolve();
    });
  });

}

export async function waitForHealthy(url, label, handles = [], timeoutMs = 45_000) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch {}
    await sleep(500);
  }

  const diagnostics = handles
    .filter((handle) => handle.label === label)
    .map(
      (handle) =>
        `${handle.label} stdout:\n${handle.getStdout()}\n${handle.label} stderr:\n${handle.getStderr()}\nlogs: ${handle.stdoutPath}, ${handle.stderrPath}`
    )
    .join("\n");

  throw new Error(`Timed out waiting for ${label} at ${url}\n${diagnostics}`);
}

export async function cleanupWindowsPorts(ports) {
  if (process.platform !== "win32") {
    return;
  }

  const output = await execFileText("netstat.exe", ["-ano"]).catch(() => "");
  const pids = new Set();

  for (const line of output.split(/\r?\n/)) {
    for (const port of ports) {
      if (line.includes(`:${port}`) && line.includes("LISTENING")) {
        const pid = line.trim().split(/\s+/).at(-1);
        if (pid && /^\d+$/.test(pid)) {
          pids.add(pid);
        }
      }
    }
  }

  await Promise.all([...pids].map((pid) => execFileText("taskkill.exe", ["/PID", pid, "/T", "/F"]).catch(() => "")));
}

export async function fetchJson(url, init = {}) {
  const response = await fetch(url, init);
  const text = await response.text();
  let body = null;

  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }

  if (!response.ok) {
    throw new Error(`Request failed for ${url}: ${response.status} ${JSON.stringify(body)}`);
  }

  return body;
}

export async function fetchText(url, init = {}) {
  const response = await fetch(url, init);
  const body = await response.text();
  if (!response.ok) {
    throw new Error(`Request failed for ${url}: ${response.status} ${body}`);
  }
  return body;
}

export function parseNdjson(text) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function resolveGoExecutable() {
  return process.platform === "win32" ? "go.exe" : "go";
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function withFileLock(lockPath, action) {
  await fs.mkdir(path.dirname(lockPath), { recursive: true });
  const timeoutMs = 240_000;
  const staleMs = 300_000;
  const start = Date.now();

  while (Date.now() - start < timeoutMs) {
    try {
      const lockHandle = await fs.open(lockPath, "wx");
      await lockHandle.writeFile(JSON.stringify({ pid: process.pid, createdAt: new Date().toISOString() }), "utf8");
      try {
        return await action();
      } finally {
        await lockHandle.close();
        await fs.rm(lockPath, { force: true });
      }
    } catch (error) {
      if (error?.code !== "EEXIST") {
        throw error;
      }
      const stat = await fs.stat(lockPath).catch(() => null);
      if (stat && Date.now() - stat.mtimeMs > staleMs) {
        await fs.rm(lockPath, { force: true }).catch(() => {});
      } else {
        await sleep(500);
      }
    }
  }

  throw new Error(`Timed out waiting for lock ${lockPath}`);
}

function execFileText(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    execFile(command, args, { windowsHide: true, ...options }, (error, stdout, stderr) => {
      if (error) {
        reject(error);
        return;
      }
      resolve(`${stdout}${stderr}`);
    });
  });
}
