"""
Web Command Executor Service

Handles real-time execution of CLI commands for the web interface,
streaming output via Server-Sent Events (SSE).
"""

import asyncio
import json
import logging
import os
import re
import shutil
import signal
import sys
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, AsyncIterator, Any, Deque
from pathlib import Path

from ..config.settings import settings


class WebCommandExecutor:
    """
    Executes CLI commands asynchronously and streams output in real-time.
    
    Features:
    - Async subprocess execution with real-time output streaming
    - Command lifecycle management (start, monitor, cancel, cleanup)
    - Execution state tracking and unique ID generation
    - Error handling and timeout management
    - Output buffering for download/display
    - Security: Command validation, bounded buffers, no shell execution
    - Output filtering to strip secrets and sensitive data
    """
    
    # Security constants
    MAX_OUTPUT_LINES = 10000  # Maximum number of output lines to buffer
    MAX_ARG_LENGTH = 1024  # Maximum length of a single argument
    MAX_ARGS_COUNT = 100  # Maximum number of arguments
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB max request payload
    
    # Command whitelist - only these commands are allowed
    ALLOWED_COMMANDS = {
        "python", "python3", "python3.9", "python3.10", "python3.11", "python3.12"
    }
    
    # Per-command argument schemas - defines allowed patterns for specific commands
    COMMAND_SCHEMAS = {
        "python": {
            "allowed_modules": {"src.main", "-m"},
            "allowed_flags": {
                # Help and info
                "--help", "-h", "--version", "-v", "--verbose", "--test-mode", "--test-data-count",
                # Output options
                "--output-dir", "--output-format", "--gamma-export", "--generate-gamma",
                # Date/time options - with strict validation
                "--start-date", "--end-date", "--time-period", "--days", "--periods-back",
                # Sample mode options
                "--count", "--save-to-file", "--no-save",
                # Analysis options
                "--multi-agent", "--analysis-type",
                "--focus-areas", "--focus-categories",
                "--max-conversations", "--parallel",
                # Agent options
                "--agent", "--agent-type", "--vendor", "--individual-breakdown", "--top-n",
                # AI model options
                "--ai-model", "--enable-fallback", "--force-standard", "--force-multi-agent",
                # Data source options
                "--board-id", "--canny-board-id", "--include-canny",
                "--include-comments", "--include-votes", "--include-trends",
                "--separate-agent-feedback",
                # Debugging and audit options
                "--audit-trail", "--analyze-troubleshooting",
                # Other options
                "--export-format", "--limit", "--category", "--subcategory", "--filter-category"
            },
            # Per-flag validation schemas
            "flag_schemas": {
                "--time-period": {"type": "enum", "values": ["yesterday", "week", "month", "quarter", "year", "6-weeks"]},
                "--days": {"type": "int", "min": 1, "max": 365},
                "--limit": {"type": "int", "min": 1, "max": 10000},
                "--top-n": {"type": "int", "min": 1, "max": 100},
                "--test-data-count": {"type": "string"},
                "--gamma-export": {"type": "enum", "values": ["pdf", "pptx"]},
                "--agent": {"type": "enum", "values": ["horatio", "boldr", "escalated"]},
                "--vendor": {"type": "enum", "values": ["horatio", "boldr"]},
                "--analysis-type": {"type": "enum", "values": ["topic-based", "synthesis", "complete"]},
                "--export-format": {"type": "enum", "values": ["json", "csv", "markdown"]},
                "--category": {"type": "enum", "values": ["Billing", "Bug", "Product Question", "Account", "Feedback", "Agent/Buddy", "Workspace", "Privacy", "Chargeback", "Partnerships", "Promotions", "Abuse", "Unknown"]},
            }
        }
    }
    
    # Shell metacharacters that are not allowed in arguments
    SHELL_METACHARACTERS = re.compile(r'[;|&$><`*?~\n\x00]')
    
    # Allowed argument patterns (for dates, numbers, etc.)
    DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    NUMBER_PATTERN = re.compile(r'^\d+$')
    IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]+$')
    
    # Patterns for filtering sensitive data from output (aligned with audit_trail.py)
    SENSITIVE_PATTERNS = [
        # Email addresses
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),
        # Bearer tokens
        (r'Bearer\s+[a-zA-Z0-9_\-\.]+', 'Bearer [TOKEN_REDACTED]'),
        # Specific API key patterns (not generic long strings that could be function names)
        (r'(sk_live_|sk_test_|pk_live_|pk_test_|rk_live_|rk_test_)[^\s\n]+', '[API_KEY_REDACTED]'),
        # AWS credentials
        (r'(AKIA[0-9A-Z]{16})', '[AWS_KEY_REDACTED]'),
        # Intercom conversation IDs (numeric)
        (r'\bconversation_id["\s:]+\d+', 'conversation_id: [ID_REDACTED]'),
        # Admin IDs in various formats
        (r'\badmin_id["\s:]+\d+', 'admin_id: [ID_REDACTED]'),
        # Environment variable secrets (key=value format)
        (r'(API_KEY|SECRET|TOKEN|PASSWORD)\s*[:=]\s*[^\s]+', r'\1: [REDACTED]'),
        # Pure hex tokens (32+ chars, lowercase only - less likely to catch function names)
        (r'\b[a-f0-9]{32,}\b', '[HEX_TOKEN_REDACTED]'),
    ]
    
    # Stack trace patterns to filter
    STACK_TRACE_PATTERNS = [
        r'Traceback \(most recent call last\):.*?(?=\n[A-Z]|\Z)',
        r'File "[^"]+", line \d+.*',
        r'^\s+at\s+.*',
    ]
    
    def __init__(self, max_output_lines: int = MAX_OUTPUT_LINES):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.active_processes: Dict[str, asyncio.subprocess.Process] = {}
        self.execution_states: Dict[str, Dict[str, Any]] = {}
        self.max_output_lines = max_output_lines
        
    def generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        return str(uuid.uuid4())
    
    def _filter_sensitive_output(self, text: str) -> str:
        """
        Filter sensitive data from output before sending to client.
        
        Removes:
        - API keys and tokens
        - AWS credentials
        - Other secrets
        
        Args:
            text: Output text to filter
            
        Returns:
            Filtered text with sensitive data redacted
        """
        filtered = text
        
        # Apply sensitive pattern filtering
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)
        
        # Stack trace filtering DISABLED for easier debugging
        # Uncomment to re-enable in production:
        # for pattern in self.STACK_TRACE_PATTERNS:
        #     filtered = re.sub(pattern, '[STACK_TRACE_REDACTED]', filtered, flags=re.DOTALL | re.MULTILINE)
        
        return filtered
    
    def _validate_command_and_args(self, command: str, args: List[str]) -> tuple[str, List[str]]:
        """
        Validate command and arguments for security.
        
        Args:
            command: The command to execute
            args: List of command arguments
            
        Returns:
            Tuple of (validated_command_path, validated_args)
            
        Raises:
            ValueError: If validation fails
        """
        # Validate command is in whitelist
        if command not in self.ALLOWED_COMMANDS:
            raise ValueError(
                f"Command '{command}' is not allowed. "
                f"Permitted commands: {', '.join(sorted(self.ALLOWED_COMMANDS))}"
            )
        
        # Resolve command to absolute path and verify it's executable
        command_path = shutil.which(command)
        if not command_path:
            raise ValueError(f"Command '{command}' not found in PATH")
        
        # Verify the command is executable
        if not os.access(command_path, os.X_OK):
            raise ValueError(f"Command '{command}' is not executable")
        
        # Validate number of arguments
        if len(args) > self.MAX_ARGS_COUNT:
            raise ValueError(f"Too many arguments (max {self.MAX_ARGS_COUNT})")
        
        # Validate each argument
        validated_args = []
        schema = self.COMMAND_SCHEMAS.get(command, {})
        flag_schemas = schema.get("flag_schemas", {})
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            # Must be a string
            if not isinstance(arg, str):
                raise ValueError(f"Argument {i} must be a string, got {type(arg).__name__}")
            
            # Check length
            if len(arg) > self.MAX_ARG_LENGTH:
                raise ValueError(
                    f"Argument {i} exceeds maximum length of {self.MAX_ARG_LENGTH} characters"
                )
            
            # Check for shell metacharacters
            if self.SHELL_METACHARACTERS.search(arg):
                raise ValueError(
                    f"Argument {i} contains disallowed shell metacharacters"
                )
            
            # Schema-based validation for recognized commands
            if schema:
                # If arg starts with --, check if it's an allowed flag
                if arg.startswith('--') or arg.startswith('-'):
                    allowed_flags = schema.get('allowed_flags', set())
                    # Extract just the flag part (before =)
                    flag_name = arg.split('=')[0]
                    if allowed_flags and flag_name not in allowed_flags:
                        raise ValueError(
                            f"Argument {i}: flag '{flag_name}' is not allowed for command '{command}'"
                        )
                    
                    # Validate flag value if schema exists
                    if flag_name in flag_schemas:
                        flag_schema = flag_schemas[flag_name]
                        
                        # Check if value is in the same arg (--flag=value) or next arg
                        if '=' in arg:
                            # Value is in same arg (e.g., --flag=value)
                            value = arg.split('=', 1)[1]
                            # Validate value based on schema
                            self._validate_flag_value(flag_name, value, flag_schema)
                            validated_args.append(arg)  # Append the whole --flag=value
                        elif i + 1 < len(args) and not args[i + 1].startswith('-'):
                            # Value is in next arg (e.g., --flag value)
                            value = args[i + 1]
                            # Validate value based on schema
                            self._validate_flag_value(flag_name, value, flag_schema)
                            validated_args.append(arg)  # Append the flag
                            validated_args.append(value)  # Append the value
                            i += 1  # Skip next arg since we already added it
                        else:
                            # Flag expects a value but none provided
                            raise ValueError(f"Argument {i}: flag '{flag_name}' requires a value")
                    else:
                        # Boolean flag or flag without schema (no value expected)
                        validated_args.append(arg)
                else:
                    # Regular argument (not a flag)
                    validated_args.append(arg)
            else:
                validated_args.append(arg)
            
            i += 1
        
        self.logger.info(f"Validated command: {command_path} with {len(validated_args)} args")
        return command_path, validated_args
    
    def _validate_flag_value(self, flag_name: str, value: str, schema: Dict[str, Any]) -> None:
        """
        Validate a flag's value against its schema.
        
        Args:
            flag_name: Name of the flag
            value: Value to validate
            schema: Schema definition for the flag
            
        Raises:
            ValueError: If validation fails
        """
        value_type = schema.get("type")
        
        if value_type == "enum":
            allowed_values = schema.get("values", [])
            if value not in allowed_values:
                raise ValueError(
                    f"Flag '{flag_name}' value '{value}' not allowed. "
                    f"Allowed values: {', '.join(allowed_values)}"
                )
        
        elif value_type == "int":
            try:
                int_value = int(value)
            except ValueError:
                raise ValueError(f"Flag '{flag_name}' requires integer value, got '{value}'")
            
            min_val = schema.get("min")
            max_val = schema.get("max")
            
            if min_val is not None and int_value < min_val:
                raise ValueError(f"Flag '{flag_name}' value {int_value} is below minimum {min_val}")
            if max_val is not None and int_value > max_val:
                raise ValueError(f"Flag '{flag_name}' value {int_value} exceeds maximum {max_val}")
        
        elif value_type == "date":
            if not self.DATE_PATTERN.match(value):
                raise ValueError(f"Flag '{flag_name}' requires date format YYYY-MM-DD, got '{value}'")
    
    def _get_project_root(self) -> Path:
        """
        Get the project root directory for command execution.
        
        Returns the configured project root from settings, or falls back to
        the parent directory of this file for non-Railway environments.
        """
        # Try to get from settings
        if hasattr(settings, 'PROJECT_ROOT') and settings.PROJECT_ROOT:
            return Path(settings.PROJECT_ROOT)
        
        # Check for Railway-specific path
        if os.path.exists("/app"):
            return Path("/app")
        
        # Fall back to project root (3 levels up from this file)
        return Path(__file__).resolve().parent.parent.parent
    
    async def _merge_async_iters(
        self, 
        stdout_iter: AsyncIterator[bytes], 
        stderr_iter: AsyncIterator[bytes],
        execution_id: str
    ) -> AsyncIterator[tuple[str, str]]:
        """
        Merge stdout and stderr async iterators to avoid deadlock.
        
        This drains both streams concurrently so neither can fill its pipe buffer
        and block the process.
        
        Args:
            stdout_iter: Async iterator for stdout lines
            stderr_iter: Async iterator for stderr lines
            execution_id: Execution ID for tracking
            
        Yields:
            Tuples of (stream_type, data) where stream_type is "stdout" or "stderr"
        """
        # Create tasks for both streams
        stdout_queue: asyncio.Queue = asyncio.Queue()
        stderr_queue: asyncio.Queue = asyncio.Queue()
        
        async def read_stream(stream_iter: AsyncIterator[bytes], stream_type: str, queue: asyncio.Queue):
            """Read from a stream and put lines into a queue."""
            try:
                async for line in stream_iter:
                    await queue.put((stream_type, line))
            except Exception as e:
                self.logger.exception(f"Error reading {stream_type} for execution {execution_id}")
            finally:
                await queue.put((stream_type, None))  # Signal end of stream
        
        # Start reader tasks
        stdout_task = asyncio.create_task(read_stream(stdout_iter, "stdout", stdout_queue))
        stderr_task = asyncio.create_task(read_stream(stderr_iter, "stderr", stderr_queue))
        
        # Track which streams are still active
        active_streams = {"stdout", "stderr"}
        
        try:
            while active_streams:
                # Wait for data from either queue
                done, pending = await asyncio.wait(
                    [
                        asyncio.create_task(stdout_queue.get()) if "stdout" in active_streams else asyncio.sleep(float('inf')),
                        asyncio.create_task(stderr_queue.get()) if "stderr" in active_streams else asyncio.sleep(float('inf'))
                    ],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in done:
                    stream_type, data = await task
                    if data is None:
                        # Stream ended
                        active_streams.discard(stream_type)
                    else:
                        yield (stream_type, data.decode('utf-8', errors='replace').rstrip())
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
        finally:
            # Ensure reader tasks are cleaned up
            stdout_task.cancel()
            stderr_task.cancel()
            try:
                await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            except asyncio.CancelledError:
                pass
    
    async def execute_command(
        self, 
        command: str, 
        args: List[str], 
        execution_id: Optional[str] = None,
        timeout: int = 1800  # 30 minutes default
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute a command and stream output in real-time.
        
        Security: Commands are validated against a whitelist, arguments are sanitized,
        and processes are executed without shell=True to prevent injection attacks.
        Output is filtered to remove sensitive data before sending to clients.
        
        Args:
            command: The command to execute (e.g., 'python')
            args: List of command arguments
            execution_id: Optional execution ID (generated if not provided)
            timeout: Maximum execution time in seconds
            
        Yields:
            Dict with output data: {"type": "stdout|stderr|status|error", "data": str, "execution_id": str}
        """
        if execution_id is None:
            execution_id = self.generate_execution_id()
        
        # Validate command and arguments
        try:
            command_path, validated_args = self._validate_command_and_args(command, args)
        except ValueError as e:
            # Validation failed - set error state and abort
            self.execution_states[execution_id] = {
                "status": "error",
                "command": command,
                "args": args,
                "start_time": datetime.now(timezone.utc),
                "output_buffer": deque(maxlen=self.max_output_lines),
                "process": None,
                "error": str(e)
            }
            yield {
                "type": "error",
                "data": f"Validation error: {str(e)}",
                "execution_id": execution_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            return
            
        # Initialize execution state with bounded buffer
        self.execution_states[execution_id] = {
            "status": "starting",
            "command": command,
            "args": validated_args,
            "start_time": datetime.now(timezone.utc),
            "output_buffer": deque(maxlen=self.max_output_lines),  # Bounded buffer
            "process": None
        }
        
        try:
            # Yield start event
            yield {
                "type": "status",
                "data": f"Starting command: {command} {' '.join(validated_args)}",
                "execution_id": execution_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Get working directory (environment-agnostic)
            cwd = str(self._get_project_root())
            
            # Create subprocess with new session for process group management
            # IMPORTANT: Using create_subprocess_exec (not shell=True) to prevent shell injection
            # Inherit current environment variables
            import os
            process_kwargs = {
                "stdout": asyncio.subprocess.PIPE,
                "stderr": asyncio.subprocess.PIPE,
                "cwd": cwd,
                "env": os.environ.copy()
            }
            
            # Start new session on Unix for process group management
            if sys.platform != "win32":
                process_kwargs["start_new_session"] = True
            
            process = await asyncio.create_subprocess_exec(
                command_path, *validated_args,
                **process_kwargs
            )
            
            # Store process reference
            self.active_processes[execution_id] = process
            self.execution_states[execution_id]["process"] = process
            self.execution_states[execution_id]["status"] = "running"
            
            # Yield running event
            yield {
                "type": "status",
                "data": "Command is running...",
                "execution_id": execution_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Stream output from both stdout and stderr concurrently to avoid deadlock
            async for stream_type, line_data in self._merge_async_iters(
                process.stdout, process.stderr, execution_id
            ):
                if line_data:  # Skip empty lines
                    # Filter sensitive data from output
                    filtered_data = self._filter_sensitive_output(line_data)
                    
                    # Buffer output with bounded deque (automatically drops oldest)
                    self.execution_states[execution_id]["output_buffer"].append({
                        "type": stream_type,
                        "data": filtered_data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    
                    yield {
                        "type": stream_type,
                        "data": filtered_data,
                        "execution_id": execution_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
            
            # Wait for process completion with timeout
            try:
                return_code = await asyncio.wait_for(process.wait(), timeout=timeout)
                
                if return_code == 0:
                    self.execution_states[execution_id]["status"] = "completed"
                    yield {
                        "type": "status",
                        "data": f"Command completed successfully (exit code: {return_code})",
                        "execution_id": execution_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    self.execution_states[execution_id]["status"] = "failed"
                    yield {
                        "type": "error",
                        "data": f"Command failed with exit code: {return_code}",
                        "execution_id": execution_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()
                self.execution_states[execution_id]["status"] = "timeout"
                yield {
                    "type": "error",
                    "data": f"Command timed out after {timeout} seconds",
                    "execution_id": execution_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            # Use logger.exception to capture full traceback
            self.logger.exception(f"Command execution error for {execution_id}")
            self.execution_states[execution_id]["status"] = "error"
            yield {
                "type": "error",
                "data": f"Execution error: {str(e)}",
                "execution_id": execution_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        finally:
            # Cleanup
            if execution_id in self.active_processes:
                del self.active_processes[execution_id]
            
            # Extract and store Gamma metadata if present
            if execution_id in self.execution_states:
                output_buffer = self.execution_states[execution_id].get("output_buffer")
                if output_buffer:
                    gamma_metadata = self._extract_gamma_metadata(output_buffer)
                    if gamma_metadata:
                        self.execution_states[execution_id]["gamma_metadata"] = gamma_metadata
                        self.logger.info(
                            "gamma_metadata_extracted",
                            execution_id=execution_id,
                            metadata_keys=list(gamma_metadata.keys())
                        )
                
                # Update final state with timezone-aware timestamp
                self.execution_states[execution_id]["end_time"] = datetime.now(timezone.utc)
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a running execution, including all child processes.
        
        Uses process group termination to ensure child processes are also killed.
        
        Args:
            execution_id: The execution ID to cancel
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        if execution_id in self.active_processes:
            process = self.active_processes[execution_id]
            try:
                # On Unix, send signal to process group to kill child processes too
                if sys.platform != "win32" and hasattr(os, 'killpg'):
                    try:
                        # Get process group ID (should be same as PID since we used start_new_session)
                        pgid = os.getpgid(process.pid)
                        # Send SIGTERM to entire process group
                        os.killpg(pgid, signal.SIGTERM)
                    except (ProcessLookupError, PermissionError, OSError) as e:
                        # Process may have already exited or we don't have permission
                        self.logger.warning(f"Failed to send SIGTERM to process group: {e}")
                        # Fall back to terminating just the parent process
                        process.terminate()
                else:
                    # Windows or no killpg support - terminate parent only
                    process.terminate()
                
                # Wait for graceful termination
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                    self.execution_states[execution_id]["status"] = "cancelled"
                    self.logger.info(f"Execution {execution_id} cancelled successfully")
                    return True
                except asyncio.TimeoutError:
                    # Force kill if terminate doesn't work
                    if sys.platform != "win32" and hasattr(os, 'killpg'):
                        try:
                            pgid = os.getpgid(process.pid)
                            os.killpg(pgid, signal.SIGKILL)
                        except (ProcessLookupError, PermissionError, OSError):
                            process.kill()
                    else:
                        process.kill()
                    
                    # Wait again after force kill
                    try:
                        await asyncio.wait_for(process.wait(), timeout=2)
                    except asyncio.TimeoutError:
                        pass  # Process is dead or zombie, continue
                    
                    self.execution_states[execution_id]["status"] = "force_killed"
                    self.logger.warning(f"Execution {execution_id} force killed")
                    return True
                    
            except Exception as e:
                self.logger.exception(f"Error cancelling execution {execution_id}")
                return False
        
        # Execution ID not found in active processes
        return False
    
    def get_execution_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get the current state of an execution."""
        return self.execution_states.get(execution_id)
    
    def get_execution_output(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get the buffered output for an execution."""
        state = self.execution_states.get(execution_id)
        if state:
            return state.get("output_buffer", [])
        return []
    
    def cleanup_old_executions(self, max_age_hours: int = 1):
        """Clean up old execution states using timezone-aware timestamps."""
        # Use timezone-aware cutoff time
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        
        to_remove = []
        for execution_id, state in self.execution_states.items():
            start_time = state.get("start_time", datetime.now(timezone.utc))
            
            # Normalize start_time to UTC timezone-aware datetime
            if start_time.tzinfo is None:
                # Naive datetime - assume UTC
                start_time = start_time.replace(tzinfo=timezone.utc)
            else:
                # Already aware - convert to UTC
                start_time = start_time.astimezone(timezone.utc)
            
            # Compare timestamps
            if start_time.timestamp() < cutoff_time:
                to_remove.append(execution_id)
        
        for execution_id in to_remove:
            del self.execution_states[execution_id]
            
        if to_remove:
            self.logger.info(f"Cleaned up {len(to_remove)} old execution states")
    
    def get_active_executions(self) -> List[str]:
        """Get list of currently active execution IDs."""
        return list(self.active_processes.keys())
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get statistics about executions."""
        total = len(self.execution_states)
        active = len(self.active_processes)
        
        status_counts = {}
        for state in self.execution_states.values():
            status = state.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_executions": total,
            "active_executions": active,
            "status_breakdown": status_counts
        }
    
    def _extract_gamma_metadata(self, output_buffer: deque) -> Optional[Dict[str, Any]]:
        """
        Extract Gamma metadata from output buffer.
        
        Args:
            output_buffer: Deque of output entries
            
        Returns:
            Dictionary with extracted metadata or None if not found
        """
        import re
        
        metadata = {}
        
        # Convert buffer to text
        output_text = ""
        for entry in output_buffer:
            if isinstance(entry, dict) and entry.get('type') in ('stdout', 'status'):
                output_text += entry.get('data', '') + "\n"
        
        # Extract Gamma URL
        url_match = re.search(r'Gamma URL:\s*(https://gamma\.app/[^\s]+)', output_text)
        if url_match:
            metadata['gamma_url'] = url_match.group(1)
        
        # Extract credits used
        credits_match = re.search(r'Credits used:\s*(\d+)', output_text)
        if credits_match:
            metadata['credits_used'] = int(credits_match.group(1))
        
        # Extract generation time
        time_match = re.search(r'Generation time:\s*([\d.]+)s', output_text)
        if time_match:
            metadata['generation_time'] = float(time_match.group(1))
        
        # Extract markdown path
        markdown_match = re.search(r'Markdown summary:\s*([^\s]+)', output_text)
        if markdown_match:
            metadata['markdown_path'] = markdown_match.group(1)
        
        return metadata if metadata else None
