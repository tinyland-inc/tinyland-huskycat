# SPDX-License-Identifier: Apache-2.0
"""
Dockerfile Validator using dockerfile library (MIT licensed)

Validates Dockerfile syntax and checks for common issues using the official
Docker parser wrapped by the dockerfile Python library.
"""

import logging
import time
from pathlib import Path
from typing import List, Set

from huskycat.validators import ValidationResult, Validator

logger = logging.getLogger(__name__)


class DockerLintValidator(Validator):
    """
    Dockerfile validator using the MIT-licensed dockerfile library.

    This validator uses the official Docker parser (via the dockerfile package)
    to validate Dockerfile syntax and identify potential issues.

    Features:
    - Syntax validation using Docker's official parser
    - Detection of common Dockerfile anti-patterns
    - Best practices recommendations
    """

    @property
    def name(self) -> str:
        return "dockerfile-lint"

    @property
    def extensions(self) -> Set[str]:
        # Return empty set - use can_handle() method instead
        return set()

    def can_handle(self, filepath: Path) -> bool:
        """Check if file is a Dockerfile or ContainerFile"""
        return filepath.name in ["Dockerfile", "ContainerFile"] or filepath.name.endswith(".dockerfile")

    def is_available(self) -> bool:
        """Check if dockerfile library is available"""
        try:
            import dockerfile  # type: ignore
            return True
        except ImportError:
            logger.warning("dockerfile library not installed. Install with: pip install dockerfile>=3.4.0")
            return False

    def validate(self, filepath: Path) -> ValidationResult:
        """Validate Dockerfile syntax and check for best practices"""
        start_time = time.time()

        try:
            import dockerfile  # type: ignore
        except ImportError:
            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=["dockerfile library not installed. Install with: pip install dockerfile>=3.4.0"],
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            # Parse the Dockerfile
            commands = dockerfile.parse_file(str(filepath))

            duration_ms = int((time.time() - start_time) * 1000)

            # Analyze commands for issues and best practices
            errors: List[str] = []
            warnings: List[str] = []

            has_from = False
            base_images = []
            run_as_root = True  # Assume root unless we see USER instruction
            has_maintainer = False
            has_healthcheck = False

            for cmd in commands:
                cmd_name = cmd.cmd.lower()

                # Check for FROM command
                if cmd_name == "from":
                    has_from = True
                    if cmd.value:
                        base_image = cmd.value[0] if isinstance(cmd.value, tuple) else str(cmd.value)
                        base_images.append(base_image)

                        # Warn about using 'latest' tag
                        if ":latest" in base_image or ":" not in base_image:
                            warnings.append(
                                f"Line {cmd.start_line}: Avoid using 'latest' tag for base image. "
                                "Pin to specific version for reproducibility."
                            )

                # Check for deprecated MAINTAINER
                elif cmd_name == "maintainer":
                    has_maintainer = True
                    warnings.append(
                        f"Line {cmd.start_line}: MAINTAINER is deprecated. "
                        "Use LABEL maintainer='email@example.com' instead."
                    )

                # Check USER instructions
                elif cmd_name == "user":
                    run_as_root = False

                # Check for HEALTHCHECK
                elif cmd_name == "healthcheck":
                    has_healthcheck = True

                # Check RUN commands for potential issues
                elif cmd_name == "run":
                    cmd_value = cmd.original.lower()

                    # Check for apt/yum without cleanup
                    if "apt-get install" in cmd_value or "apt install" in cmd_value:
                        if "rm -rf /var/lib/apt/lists/*" not in cmd_value and "apt-get clean" not in cmd_value:
                            warnings.append(
                                f"Line {cmd.start_line}: apt-get install without cleanup. "
                                "Consider adding: && rm -rf /var/lib/apt/lists/*"
                            )

                    if "yum install" in cmd_value or "dnf install" in cmd_value:
                        if "yum clean all" not in cmd_value and "dnf clean all" not in cmd_value:
                            warnings.append(
                                f"Line {cmd.start_line}: yum/dnf install without cleanup. "
                                "Consider adding: && yum clean all"
                            )

                    # Check for sudo usage
                    if "sudo" in cmd_value:
                        warnings.append(
                            f"Line {cmd.start_line}: Avoid using 'sudo' in RUN commands. "
                            "Docker runs as root by default."
                        )

                # Check COPY/ADD commands
                elif cmd_name in ["copy", "add"]:
                    if cmd_name == "add" and cmd.value:
                        # ADD should only be used for tar extraction
                        source = cmd.value[0] if isinstance(cmd.value, tuple) and len(cmd.value) > 0 else ""
                        if not (isinstance(source, str) and (source.endswith(".tar") or source.endswith(".tar.gz") or source.startswith("http"))):
                            warnings.append(
                                f"Line {cmd.start_line}: Use COPY instead of ADD for files. "
                                "ADD should only be used for tar extraction or URLs."
                            )

            # Check for required FROM command
            if not has_from:
                errors.append("Dockerfile must contain at least one FROM instruction")

            # Security recommendations
            if run_as_root and base_images:
                warnings.append(
                    "No USER instruction found. Consider running as non-root user for security. "
                    "Add: RUN useradd -m myuser && USER myuser"
                )

            # Best practice recommendations
            if not has_healthcheck and base_images:
                warnings.append(
                    "No HEALTHCHECK instruction found. Consider adding health check for container monitoring."
                )

            # Determine success
            success = len(errors) == 0

            if success and len(warnings) == 0:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=True,
                    messages=["Dockerfile syntax is valid"],
                    duration_ms=duration_ms,
                )
            else:
                return ValidationResult(
                    tool=self.name,
                    filepath=str(filepath),
                    success=success,
                    errors=errors,
                    warnings=warnings,
                    messages=["Dockerfile parsed successfully"] if success else [],
                    duration_ms=duration_ms,
                )

        except Exception as e:
            # Handle parsing errors
            error_msg = str(e)

            # Extract line number if available in error message
            line_info = ""
            if "line" in error_msg.lower():
                line_info = error_msg
            else:
                line_info = f"Parse error: {error_msg}"

            return ValidationResult(
                tool=self.name,
                filepath=str(filepath),
                success=False,
                errors=[f"Dockerfile syntax error: {line_info}"],
                duration_ms=int((time.time() - start_time) * 1000),
            )
