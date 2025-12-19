"""
Process Manager for Non-Blocking Git Hook Execution.

Provides fork-based execution for git hooks with:
- Immediate return to git (<100ms)
- Background validation with TUI
- Result caching and persistence
- PID file management
- Zombie process cleanup
- Previous run failure handling

Key Design:
- Parent process returns immediately to git
- Child process runs full validation with progress UI
- Results cached in .huskycat/runs/{run_id}.json
- Previous failed runs require user confirmation to proceed
"""

import logging
import os
import signal
import sys
import json
import time
import psutil
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationRun:
    """
    Represents a single validation run with results.

    Attributes:
        run_id: Unique identifier (ISO timestamp)
        started: ISO timestamp when validation started
        completed: ISO timestamp when validation completed (None if running)
        files: List of files validated
        success: Whether validation passed
        tools_run: List of tool names executed
        errors: Number of errors found
        warnings: Number of warnings found
        exit_code: Process exit code (0=success, non-zero=failure)
        pid: Process ID of validation run
    """

    run_id: str
    started: str
    completed: Optional[str] = None
    files: List[str] = None
    success: bool = False
    tools_run: List[str] = None
    errors: int = 0
    warnings: int = 0
    exit_code: Optional[int] = None
    pid: Optional[int] = None

    def __post_init__(self):
        """Initialize mutable default values."""
        if self.files is None:
            self.files = []
        if self.tools_run is None:
            self.tools_run = []


class ProcessManager:
    """
    Manages forked validation processes for git hooks.

    Features:
    - Fork validation to background process
    - Track running validations via PID files
    - Cache validation results for quick checks
    - Handle previous failure scenarios with user prompts
    - Cleanup zombie processes
    - Prevent duplicate validations
    """

    def __init__(self, cache_dir: Path = None):
        """
        Initialize process manager.

        Args:
            cache_dir: Directory for run results (default: .huskycat/runs)
        """
        if cache_dir is None:
            cache_dir = Path.cwd() / ".huskycat" / "runs"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.pids_dir = self.cache_dir / "pids"
        self.pids_dir.mkdir(parents=True, exist_ok=True)

        self.logs_dir = self.cache_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # File to track last validation run
        self.last_run_file = self.cache_dir / "last_run.json"

    def check_previous_run(self) -> Optional[ValidationRun]:
        """
        Check if previous validation failed and return the run details.

        Returns:
            ValidationRun if previous run failed, None otherwise
        """
        if not self.last_run_file.exists():
            return None

        try:
            data = json.loads(self.last_run_file.read_text())
            run = ValidationRun(**data)

            # Only care about failed runs
            if not run.success and run.completed is not None:
                return run

            return None
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Could not parse last run: {e}")
            return None

    def handle_previous_failure(self, run: ValidationRun) -> bool:
        """
        Handle previous failed run with user prompt.

        Args:
            run: The previous failed ValidationRun

        Returns:
            True if user wants to proceed, False to abort commit
        """
        # Check if TTY is available for interactive prompt
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            # Non-interactive: fail to be safe
            print(f"ERROR: Previous validation failed ({run.errors} errors)")
            print(f"       Run 'huskycat validate' to fix issues before committing")
            return False

        # Calculate time since failure
        try:
            failed_time = datetime.fromisoformat(run.completed)
            elapsed = datetime.now() - failed_time
            time_str = self._format_elapsed_time(elapsed)
        except (ValueError, TypeError):
            time_str = "unknown time ago"

        # Show failure details
        print(f"\n  Previous validation FAILED ({time_str})")
        print(f"    Errors:   {run.errors}")
        print(f"    Warnings: {run.warnings}")
        print(f"    Tools:    {', '.join(run.tools_run)}")

        # Prompt user
        print("\n  Proceed with commit anyway? [y/N] ", end="", flush=True)

        try:
            response = sys.stdin.readline().strip().lower()
            proceed = response in ["y", "yes"]

            if proceed:
                print("  Proceeding despite validation failure...\n")
                # Clear the failed run so we don't keep asking
                self._clear_last_run()
            else:
                print("  Aborting commit. Fix validation issues first.\n")

            return proceed
        except (KeyboardInterrupt, EOFError):
            print("\n  Aborting commit.\n")
            return False

    def fork_validation(
        self, files: List[str], validation_cmd: str, validation_args: List[str] = None
    ) -> int:
        """
        Fork and run validation in child process.

        Parent process returns immediately with PID.
        Child process runs full validation and saves results.

        Args:
            files: List of files to validate
            validation_cmd: Command to execute for validation
            validation_args: Additional arguments for validation command

        Returns:
            PID of child process (parent returns this)
            Does not return in child (calls sys.exit)
        """
        # Create unique run ID
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # Check if validation already running for these files
        if self._is_running(files):
            print("  Validation already running for these files")
            return 0

        # Fork process
        try:
            pid = os.fork()
        except OSError as e:
            logger.error(f"Fork failed: {e}")
            print(f"ERROR: Could not fork validation process: {e}")
            return -1

        if pid > 0:
            # PARENT PROCESS: Save PID and return immediately
            self._save_pid(pid, run_id, files)

            log_file = self.logs_dir / f"{run_id}.log"
            print(f"  Validation running in background (PID {pid})")
            print(f"  View progress: tail -f {log_file}")
            print()

            return pid
        else:
            # CHILD PROCESS: Run validation
            self._run_validation_child(run_id, files, validation_cmd, validation_args)
            # Never returns - child exits

    def _run_validation_child(
        self,
        run_id: str,
        files: List[str],
        validation_cmd: str,
        validation_args: List[str] = None,
    ):
        """
        Child process: Run validation and save results.

        This function runs in the forked child process and handles:
        - Redirecting stdout/stderr to log file
        - Executing validation command
        - Capturing results
        - Saving run results
        - Cleaning up PID file
        - Exiting with appropriate code
        """
        log_file = self.logs_dir / f"{run_id}.log"

        try:
            # Redirect stdout/stderr to log file
            log_fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            os.dup2(log_fd, sys.stdout.fileno())
            os.dup2(log_fd, sys.stderr.fileno())
            os.close(log_fd)

            # Create validation run record
            run = ValidationRun(
                run_id=run_id,
                started=datetime.now().isoformat(),
                files=files,
                tools_run=[],
                pid=os.getpid(),
            )

            print(f"Starting validation at {run.started}")
            print(f"Files: {len(files)}")
            print(f"Command: {validation_cmd} {' '.join(validation_args or [])}")
            print("-" * 60)

            # Build full command
            import subprocess

            cmd = [validation_cmd] + (validation_args or [])

            # Run validation command
            result = subprocess.run(
                cmd, capture_output=False, text=True  # Already redirected
            )

            # Update run with results
            run.completed = datetime.now().isoformat()
            run.exit_code = result.returncode
            run.success = result.returncode == 0

            # Save run results
            self.save_run(run)

            print("-" * 60)
            print(f"Validation completed at {run.completed}")
            print(f"Exit code: {run.exit_code}")
            print(f"Success: {run.success}")

            # Cleanup PID file
            self._remove_pid(os.getpid())

            # Exit with validation exit code
            sys.exit(result.returncode)

        except Exception as e:
            # Log error and exit with failure
            try:
                print(f"FATAL ERROR in validation child process: {e}", file=sys.stderr)
                import traceback

                traceback.print_exc(file=sys.stderr)
            except Exception:
                pass

            # Try to cleanup
            try:
                self._remove_pid(os.getpid())
            except Exception:
                pass

            sys.exit(1)

    def save_run(self, run: ValidationRun):
        """
        Persist validation run results to cache.

        Args:
            run: ValidationRun to save
        """
        run_file = self.cache_dir / f"{run.run_id}.json"

        try:
            run_file.write_text(json.dumps(asdict(run), indent=2))

            # Update last run pointer
            self.last_run_file.write_text(json.dumps(asdict(run), indent=2))

            logger.debug(f"Saved validation run: {run.run_id}")
        except Exception as e:
            logger.error(f"Could not save validation run: {e}")

    def get_running_validations(self) -> List[Dict[str, Any]]:
        """
        Get list of currently running validation processes.

        Returns:
            List of dictionaries with pid, run_id, files, started
        """
        running = []

        for pid_file in self.pids_dir.glob("*.json"):
            try:
                data = json.loads(pid_file.read_text())
                pid = data.get("pid")

                # Check if process is still running
                if pid and self._is_process_alive(pid):
                    running.append(data)
                else:
                    # Cleanup stale PID file
                    pid_file.unlink()
            except Exception as e:
                logger.warning(f"Error reading PID file {pid_file}: {e}")

        return running

    def cleanup_zombies(self):
        """
        Clean up completed child processes (reap zombies).

        Uses os.waitpid with WNOHANG to reap any completed children
        without blocking.
        """
        while True:
            try:
                # Reap any completed child process
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    # No more children to reap
                    break

                logger.debug(f"Reaped zombie process PID {pid} (status={status})")
                self._remove_pid(pid)
            except ChildProcessError:
                # No child processes
                break
            except Exception as e:
                logger.warning(f"Error cleaning up zombies: {e}")
                break

    def _save_pid(self, pid: int, run_id: str, files: List[str]):
        """Save PID file for running validation."""
        pid_file = self.pids_dir / f"{pid}.json"

        data = {
            "pid": pid,
            "run_id": run_id,
            "files": files,
            "started": datetime.now().isoformat(),
        }

        try:
            pid_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Could not save PID file: {e}")

    def _remove_pid(self, pid: int):
        """Remove PID file for completed validation."""
        pid_file = self.pids_dir / f"{pid}.json"

        try:
            if pid_file.exists():
                pid_file.unlink()
                logger.debug(f"Removed PID file for {pid}")
        except Exception as e:
            logger.warning(f"Could not remove PID file: {e}")

    def _is_running(self, files: List[str]) -> bool:
        """
        Check if validation is already running for these files.

        Args:
            files: List of files to check

        Returns:
            True if validation already running for any of these files
        """
        running = self.get_running_validations()
        files_set = set(files)

        for run in running:
            run_files = set(run.get("files", []))
            # Check if there's any overlap in files
            if files_set & run_files:
                return True

        return False

    def _is_process_alive(self, pid: int) -> bool:
        """
        Check if a process is still running.

        Args:
            pid: Process ID to check

        Returns:
            True if process is alive, False otherwise
        """
        try:
            # Use psutil for robust process checking
            return psutil.pid_exists(pid)
        except Exception:
            # Fallback to os.kill with signal 0
            try:
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False

    def _clear_last_run(self):
        """Clear the last run tracking file."""
        try:
            if self.last_run_file.exists():
                self.last_run_file.unlink()
        except Exception as e:
            logger.warning(f"Could not clear last run: {e}")

    def _format_elapsed_time(self, elapsed: timedelta) -> str:
        """
        Format elapsed time in human-readable format.

        Args:
            elapsed: timedelta object

        Returns:
            Human-readable string like "2 minutes ago"
        """
        seconds = int(elapsed.total_seconds())

        if seconds < 60:
            return f"{seconds} seconds ago"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"

    def get_run_history(self, limit: int = 10) -> List[ValidationRun]:
        """
        Get recent validation run history.

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of ValidationRun objects, most recent first
        """
        runs = []

        # Get all run files
        run_files = sorted(
            self.cache_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        for run_file in run_files[:limit]:
            # Skip special files
            if run_file.name == "last_run.json":
                continue

            try:
                data = json.loads(run_file.read_text())
                runs.append(ValidationRun(**data))
            except Exception as e:
                logger.warning(f"Could not load run {run_file}: {e}")

        return runs

    def cleanup_old_runs(self, max_age_days: int = 7):
        """
        Clean up old validation run files.

        Args:
            max_age_days: Remove runs older than this many days
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        removed = 0

        for run_file in self.cache_dir.glob("*.json"):
            # Skip special files
            if run_file.name == "last_run.json":
                continue

            try:
                # Check file age
                mtime = datetime.fromtimestamp(run_file.stat().st_mtime)
                if mtime < cutoff:
                    run_file.unlink()
                    removed += 1
            except Exception as e:
                logger.warning(f"Error cleaning up {run_file}: {e}")

        if removed > 0:
            logger.info(f"Cleaned up {removed} old validation runs")


# Convenience function for git hooks integration
def should_proceed_with_commit(cache_dir: Path = None) -> bool:
    """
    Check if commit should proceed based on previous validation.

    This is the main entry point for git hooks to check if there's
    a previous failed validation that needs user confirmation.

    Args:
        cache_dir: Directory for run results (default: .huskycat/runs)

    Returns:
        True if commit should proceed, False to abort
    """
    manager = ProcessManager(cache_dir)

    # Cleanup any zombies first
    manager.cleanup_zombies()

    # Check for previous failure
    previous_run = manager.check_previous_run()

    if previous_run is None:
        # No previous failure, proceed
        return True

    # Handle previous failure (prompts user)
    return manager.handle_previous_failure(previous_run)
