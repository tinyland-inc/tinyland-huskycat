"""
Base command classes for HuskyCat validation platform.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .adapters.base import ModeAdapter


class CommandStatus(Enum):
    """Status of a command execution."""

    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class CommandResult:
    """Result from a command execution."""

    status: CommandStatus
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class BaseCommand(ABC):
    """Abstract base class for all commands."""

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        verbose: bool = False,
        adapter: Optional["ModeAdapter"] = None,
    ):
        """
        Initialize the command.

        Args:
            config_dir: Directory containing configuration files
            verbose: Enable verbose output
            adapter: Mode adapter for mode-specific behavior
        """
        self.config_dir = config_dir or Path.home() / ".huskycat"
        self.verbose = verbose
        self.adapter = adapter
        self.config_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> CommandResult:
        """
        Execute the command.

        Returns:
            CommandResult with status and any output data
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the command name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Get the command description."""

    def validate_prerequisites(self) -> CommandResult:
        """
        Validate that prerequisites for the command are met.

        Returns:
            CommandResult indicating if prerequisites are satisfied
        """
        return CommandResult(
            status=CommandStatus.SUCCESS, message="Prerequisites satisfied"
        )

    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{level}] {message}")
