# Codebase Improvement Analysis

This document categorizes potential improvements by priority (P0 = critical, P1 = important, P2 = nice-to-have).

## P0 (Critical - Data Loss, Security, Correctness)

### 1. Binary Path Validation Inconsistency
**Location**: `smi_bench/rust.py`, `smi_bench/runner.py`, `smi_bench/inhabit_runner.py`

**Issue**: `default_rust_binary()` can return a `Path` that doesn't exist, but callers check `.exists()` inconsistently. If the binary is missing, errors occur late in execution.

**Impact**: 
- Late failure after setup work
- Unclear error messages
- Potential for silent failures if error handling swallows exceptions

**Recommendation**:
- Add `validate_rust_binary(path: Path) -> Path` helper that raises `FileNotFoundError` with clear message
- Use it consistently at startup in both runners
- Consider checking executable permissions too

**Example fix**:
```python
def validate_rust_binary(path: Path) -> Path:
    """Validate that the Rust binary exists and is executable."""
    if not path.exists():
        raise FileNotFoundError(
            f"Rust binary not found: {path}\n"
            f"Run: cargo build --release --locked"
        )
    if not os.access(path, os.X_OK):
        raise PermissionError(f"Rust binary not executable: {path}")
    return path
```

### 2. Temporary File Cleanup is Best-Effort
**Location**: `smi_bench/inhabit_runner.py` (lines 397-400, 461-490)

**Issue**: Temp files are created in `benchmark/.tmp/` but cleanup uses `try/except: pass`, which can silently fail. The `.tmp` directory can accumulate files over time.

**Impact**:
- Disk space leaks
- Potential security issue if temp files contain sensitive data
- Debugging confusion (old temp files)

**Recommendation**:
- Use `tempfile.TemporaryDirectory` context manager for automatic cleanup
- Or add explicit cleanup on successful completion
- Consider periodic cleanup of old temp files (>24h)

**Example fix**:
```python
from tempfile import TemporaryDirectory
import atexit

# At module level or startup
_tmp_cleanup_registry: list[Path] = []

def _cleanup_old_tmp_files(tmp_dir: Path, max_age_seconds: int = 86400) -> None:
    """Remove temp files older than max_age_seconds."""
    now = time.time()
    for p in tmp_dir.glob("ptb_spec_*.json"):
        try:
            if now - p.stat().st_mtime > max_age_seconds:
                p.unlink()
        except Exception:
            pass
```

### 3. Checkpoint File Corruption Risk
**Location**: `smi_bench/runner.py` (lines 247-248), `smi_bench/inhabit_runner.py` (line 679)

**Issue**: Atomic writes use `.tmp` suffix + `replace()`, but if the process crashes mid-write, the `.tmp` file remains. On resume, the checkpoint might be corrupted.

**Impact**:
- Data loss if checkpoint is corrupted
- Unclear error messages when resuming fails

**Recommendation**:
- Add checksum validation (e.g., JSON schema validation or hash)
- Detect and handle corrupted checkpoints gracefully
- Consider using `atomicwrites` library for better atomicity

**Example fix**:
```python
import hashlib

def _write_checkpoint_safe(out_path: Path, run_result: RunResult) -> None:
    """Write checkpoint atomically with validation."""
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    data = asdict(run_result)
    json_str = json.dumps(data, indent=2, sort_keys=True)
    # Add checksum
    checksum = hashlib.sha256(json_str.encode()).hexdigest()[:8]
    data["_checksum"] = checksum
    json_str = json.dumps(data, indent=2, sort_keys=True)
    tmp.write_text(json_str + "\n")
    tmp.replace(out_path)
```

### 4. JSON Parsing Error Context Loss
**Location**: Multiple files (`runner.py`, `inhabit_runner.py`, `json_extract.py`, etc.)

**Issue**: Many places catch `json.JSONDecodeError` or generic `Exception` without preserving context (file path, input snippet).

**Impact**:
- Hard to debug JSON parsing failures
- Lost error context makes troubleshooting slow

**Recommendation**:
- Wrap JSON parsing in helper that adds context
- Log the problematic JSON snippet (truncated) for debugging

**Example fix**:
```python
def safe_json_loads(text: str, *, context: str = "") -> dict:
    """Parse JSON with better error messages."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        snippet = text[max(0, e.pos - 50):e.pos + 50]
        raise ValueError(
            f"JSON parse error in {context}: {e.msg}\n"
            f"Position {e.pos}, snippet: ...{snippet}..."
        ) from e
```

## P1 (Important - Robustness, Maintainability)

### 5. Too Many Bare `except Exception` Blocks
**Location**: Throughout codebase (115+ matches)

**Issue**: Many `except Exception:` blocks swallow all errors, making debugging difficult.

**Impact**:
- Silent failures
- Lost error context
- Hard to diagnose issues

**Recommendation**:
- Be more specific about exception types
- Always log exceptions before swallowing
- Use `except Exception as e: logger.error(...); raise` pattern for critical paths

**Example locations to fix**:
- `runner.py:299` - checkpoint resume error handling
- `inhabit_runner.py:451` - dry-run fallback
- `dataset.py:29` - metadata parsing

### 6. Subprocess Calls Without Timeout
**Location**: `smi_bench/rust.py` (line 48), some calls in `inhabit_runner.py`

**Issue**: `subprocess.check_output()` in `emit_bytecode_json()` has no timeout. If the Rust binary hangs, the benchmark hangs indefinitely.

**Impact**:
- Benchmark can hang forever
- No way to recover from stuck processes

**Recommendation**:
- Add reasonable timeouts (e.g., 60s for interface extraction)
- Consider making timeout configurable

**Example fix**:
```python
def emit_bytecode_json(*, package_dir: Path, rust_bin: Path, timeout_s: float = 60.0) -> dict:
    """..."""
    out = subprocess.check_output(
        [...],
        text=True,
        timeout=timeout_s,  # Add timeout
    )
    return json.loads(out)
```

### 7. Checkpoint Resume Robustness
**Location**: `smi_bench/runner.py` (lines 279-290), `smi_bench/inhabit_runner.py` (lines 669-690)

**Issue**: Checkpoint loading can fail silently (e.g., `except Exception: continue` in resume logic). Malformed checkpoints can cause partial resume.

**Impact**:
- Silent data loss on resume
- Unclear why some packages are skipped

**Recommendation**:
- Validate checkpoint schema version upfront
- Log warnings for skipped packages
- Add `--strict-checkpoint` flag to fail fast on corruption

### 8. Temp Directory Accumulation
**Location**: `smi_bench/inhabit_runner.py` (lines 458-460)

**Issue**: `benchmark/.tmp/` directory is created but never cleaned up. Files accumulate over time.

**Impact**:
- Disk space waste
- Cluttered temp directory

**Recommendation**:
- Add cleanup on startup (remove files >24h old)
- Or use `tempfile.mkdtemp()` with cleanup on exit

### 9. Binary Executable Permission Check Missing
**Location**: `smi_bench/rust.py`, `smi_bench/inhabit_runner.py`

**Issue**: Code checks `.exists()` but not `.is_file()` or executable permissions.

**Impact**:
- Unclear error if binary exists but isn't executable
- Could fail late with cryptic error

**Recommendation**:
- Add permission check (see P0 #1)

## P2 (Nice-to-Have - Polish, Optimization)

### 10. Better Error Messages
**Location**: Throughout

**Issue**: Some error messages are terse or lack context (e.g., "rust binary not found" without suggesting fix).

**Recommendation**:
- Add "Did you mean..." suggestions
- Include command-line examples in error messages
- Link to relevant docs

### 11. Structured Logging Improvements
**Location**: `smi_bench/logging.py`

**Issue**: JSONL logging is good, but could add more structured fields (e.g., package_id in all events, timing metadata).

**Recommendation**:
- Add consistent event schema
- Include timing metadata automatically
- Consider adding log levels (DEBUG, INFO, WARN, ERROR)

### 12. Configuration Validation Upfront
**Location**: `smi_bench/agents/real_agent.py`, `smi_bench/runner.py`

**Issue**: Configuration errors (e.g., invalid API key format) are discovered late (during first LLM call).

**Recommendation**:
- Validate all config at startup
- Fail fast with clear messages
- Add `--validate-config` flag

### 13. Progress Reporting Enhancements
**Location**: `smi_bench/runner.py`, `smi_bench/inhabit_runner.py`

**Issue**: Progress bars are basic. Could show ETA, throughput, error rate.

**Recommendation**:
- Add ETA calculation
- Show error rate in progress bar
- Add summary stats at end

### 14. Type Hints Completeness
**Location**: Some functions still use `dict` without `dict[str, Any]` or more specific types

**Issue**: Incomplete type hints reduce IDE support and static analysis benefits.

**Recommendation**:
- Add type hints to all public functions
- Use `TypedDict` for structured dicts (e.g., checkpoint schema)

### 15. Test Coverage Gaps
**Location**: `benchmark/tests/`

**Issue**: Some edge cases aren't tested (e.g., corrupted checkpoints, missing binaries, timeout handling).

**Recommendation**:
- Add tests for error paths
- Add integration tests for full runs
- Test checkpoint resume with various failure modes

---

## Implementation Priority

**Immediate (P0)**:
1. Binary validation (#1)
2. Temp file cleanup (#2)
3. Checkpoint corruption handling (#3)

**Short-term (P1)**:
4. Exception handling improvements (#5)
5. Subprocess timeouts (#6)
6. Checkpoint resume robustness (#7)

**Long-term (P2)**:
7. Error message polish (#10)
8. Logging improvements (#11)
9. Test coverage (#15)
