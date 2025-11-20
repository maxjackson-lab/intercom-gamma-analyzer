"""
Execution State Manager

Manages in-memory state for web command executions, including
tracking active executions, queuing, and cleanup.
"""

import asyncio
import logging
import json
from pathlib import Path
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Deque
from dataclasses import dataclass, asdict, field
from enum import Enum


class ExecutionStatus(Enum):
    """Execution status enumeration."""
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ExecutionState:
    """Execution state data structure with bounded output buffer."""
    execution_id: str
    command: str
    args: List[str]
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    output_buffer: Optional[Deque[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    return_code: Optional[int] = None
    queue_position: Optional[int] = None
    gamma_metadata: Optional[Dict[str, Any]] = None  # Store Gamma generation metadata
    audit_files: List[str] = field(default_factory=list)  # Track audit trail files
    output_files: List[str] = field(default_factory=list)  # Track all output files
    max_output_buffer_size: int = 1000  # Maximum number of output entries to keep
    
    def __post_init__(self):
        """Initialize output buffer as bounded deque if not provided."""
        if self.output_buffer is None:
            self.output_buffer = deque(maxlen=self.max_output_buffer_size)


class ExecutionStateManager:
    """
    Manages execution state in memory for the web interface.
    
    Features:
    - Thread-safe state management with asyncio locks
    - Execution queuing with position tracking
    - Automatic cleanup of old executions
    - Concurrent execution limits
    - State persistence for downloads
    - Cancellation signal tracking
    """
    
    def __init__(self, max_concurrent: int = 5, max_queue_size: int = 20, persistence_dir: str = "/app/outputs/jobs"):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.persistence_dir = Path(persistence_dir)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Create persistence directory
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
        
        # State storage
        self._executions: Dict[str, ExecutionState] = {}
        self._queue: List[str] = []  # List of execution IDs in queue order
        self._active: List[str] = []  # List of currently running execution IDs
        self._cancellation_signals: Dict[str, bool] = {}  # Track cancellation requests
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "total_executions": 0,
            "completed_executions": 0,
            "failed_executions": 0,
            "cancelled_executions": 0,
            "queue_full_rejections": 0
        }
        
        # Load existing jobs from disk
        self._load_from_disk()
    
    async def create_execution(
        self, 
        execution_id: str, 
        command: str, 
        args: List[str]
    ) -> ExecutionState:
        """
        Create a new execution state.
        
        Args:
            execution_id: Unique execution identifier
            command: Command to execute
            args: Command arguments
            
        Returns:
            ExecutionState object
            
        Raises:
            ValueError: If queue is full
        """
        async with self._lock:
            # Check if we can accept new executions
            if len(self._queue) >= self.max_queue_size:
                self._stats["queue_full_rejections"] += 1
                raise ValueError(f"Queue is full (max {self.max_queue_size} executions)")
            
            # Create execution state
            execution = ExecutionState(
                execution_id=execution_id,
                command=command,
                args=args,
                status=ExecutionStatus.QUEUED,
                start_time=datetime.now(),
                queue_position=len(self._queue) + 1
            )
            
            # Add to state storage
            self._executions[execution_id] = execution
            self._queue.append(execution_id)
            self._stats["total_executions"] += 1
            
            # Save to disk for persistence
            self._save_to_disk(execution_id)
            
            self.logger.info(f"Created execution {execution_id} (queue position: {execution.queue_position})")
            return execution
    
    async def start_execution(self, execution_id: str) -> bool:
        """
        Move an execution from queue to active.
        
        Args:
            execution_id: Execution ID to start
            
        Returns:
            True if started successfully, False if not available or at limit
        """
        async with self._lock:
            if execution_id not in self._executions:
                return False
            
            if len(self._active) >= self.max_concurrent:
                return False
            
            if execution_id not in self._queue:
                return False
            
            # Move from queue to active
            self._queue.remove(execution_id)
            self._active.append(execution_id)
            
            # Update execution state
            execution = self._executions[execution_id]
            execution.status = ExecutionStatus.STARTING
            execution.queue_position = None
            
            # Update queue positions for remaining queued executions
            for i, queued_id in enumerate(self._queue):
                self._executions[queued_id].queue_position = i + 1
            
            self.logger.info(f"Started execution {execution_id}")
            return True
    
    async def update_execution_status(
        self, 
        execution_id: str, 
        status: ExecutionStatus,
        error_message: Optional[str] = None,
        return_code: Optional[int] = None
    ):
        """Update execution status."""
        async with self._lock:
            if execution_id in self._executions:
                execution = self._executions[execution_id]
                execution.status = status
                
                if error_message:
                    execution.error_message = error_message
                
                if return_code is not None:
                    execution.return_code = return_code
                
                if status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, 
                            ExecutionStatus.CANCELLED, ExecutionStatus.TIMEOUT, ExecutionStatus.ERROR]:
                    execution.end_time = datetime.now()
                    
                    # Remove from active list
                    if execution_id in self._active:
                        self._active.remove(execution_id)
                    
                    # Update statistics
                    if status == ExecutionStatus.COMPLETED:
                        self._stats["completed_executions"] += 1
                    elif status == ExecutionStatus.FAILED:
                        self._stats["failed_executions"] += 1
                    elif status == ExecutionStatus.CANCELLED:
                        self._stats["cancelled_executions"] += 1
                
                # Save to disk after status update
                self._save_to_disk(execution_id)
                
                self.logger.info(f"Updated execution {execution_id} status to {status.value}")
    
    async def add_output(self, execution_id: str, output_data: Dict[str, Any]):
        """Add output data to execution buffer."""
        async with self._lock:
            if execution_id in self._executions:
                self._executions[execution_id].output_buffer.append(output_data)
    
    async def add_audit_file(self, execution_id: str, audit_file_path: str) -> bool:
        """
        Add audit file to execution state.
        
        Args:
            execution_id: The execution ID
            audit_file_path: Path to the audit file (relative or absolute)
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            async with self._lock:
                if execution_id not in self._executions:
                    self.logger.warning(f"Execution {execution_id} not found for audit file tracking")
                    return False
                
                execution = self._executions[execution_id]
                
                # Extract filename from path
                filename = Path(audit_file_path).name
                
                # Add to audit_files if not already present
                if filename not in execution.audit_files:
                    execution.audit_files.append(filename)
                    self.logger.info(f"Added audit file {filename} to execution {execution_id}")
                    
                    # Also add to output_files
                    if filename not in execution.output_files:
                        execution.output_files.append(filename)
                    
                    # Save to disk
                    self._save_to_disk(execution_id)
                    
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add audit file for {execution_id}: {e}")
            return False
    
    async def add_output_file(self, execution_id: str, file_path: str) -> bool:
        """
        Add output file to execution state.
        
        Args:
            execution_id: The execution ID
            file_path: Path to the output file
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            async with self._lock:
                if execution_id not in self._executions:
                    return False
                
                execution = self._executions[execution_id]
                filename = Path(file_path).name
                
                if filename not in execution.output_files:
                    execution.output_files.append(filename)
                    self._save_to_disk(execution_id)
                    
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add output file for {execution_id}: {e}")
            return False
    
    async def get_execution(self, execution_id: str) -> Optional[ExecutionState]:
        """Get execution state by ID."""
        async with self._lock:
            return self._executions.get(execution_id)
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        async with self._lock:
            return {
                "queue_length": len(self._queue),
                "active_count": len(self._active),
                "max_concurrent": self.max_concurrent,
                "max_queue_size": self.max_queue_size,
                "queue_positions": {
                    exec_id: self._executions[exec_id].queue_position 
                    for exec_id in self._queue
                }
            }
    
    async def get_next_queued_execution(self) -> Optional[str]:
        """Get the next execution ID from the queue."""
        async with self._lock:
            if self._queue and len(self._active) < self.max_concurrent:
                return self._queue[0]
            return None
    
    async def cleanup_old_executions(
        self,
        max_age_days: int = 14,
        max_count: int = 50,
        cleanup_files: bool = True
    ) -> Dict[str, int]:
        """
        Clean up old execution states and files based on retention policy.
        
        Args:
            max_age_days: Delete executions older than this many days (default: 14)
            max_count: Keep at most this many recent executions (default: 50)
            cleanup_files: Also delete associated output and audit files (default: True)
        
        Returns:
            Dict with cleanup statistics:
            - deleted_executions: Number of execution states deleted
            - deleted_files: Number of files deleted
            - remaining_executions: Number of executions remaining
        """
        async with self._lock:
            now = datetime.now()
            cutoff_date = now - timedelta(days=max_age_days)
            
            # Get completed executions sorted by date (oldest first)
            completed_executions = [
                (exec_id, state) for exec_id, state in self._executions.items()
                if state.status in [
                    ExecutionStatus.COMPLETED,
                    ExecutionStatus.FAILED,
                    ExecutionStatus.CANCELLED,
                    ExecutionStatus.TIMEOUT,
                    ExecutionStatus.ERROR
                ]
            ]
            
            completed_executions.sort(
                key=lambda x: x[1].start_time,
                reverse=False  # Oldest first
            )
            
            deleted_count = 0
            deleted_files = 0
            kept_recent = set()
            
            # Keep last N executions regardless of age
            if len(completed_executions) > max_count:
                for exec_id, state in completed_executions[-max_count:]:
                    kept_recent.add(exec_id)
            
            # Delete old executions
            for exec_id, state in completed_executions:
                # Skip if in "keep recent" set
                if exec_id in kept_recent:
                    continue
                
                # Check age
                started_at = state.start_time
                if started_at > cutoff_date:
                    continue
                
                # Delete output files if requested
                if cleanup_files:
                    # Delete all tracked output files
                    for filename in state.output_files:
                        filepath = Path("/app/outputs") / filename
                        if filepath.exists():
                            try:
                                filepath.unlink()
                                deleted_files += 1
                                self.logger.info(f"Deleted output file: {filename}")
                            except Exception as e:
                                self.logger.error(f"Failed to delete {filename}: {e}")
                    
                    # Delete audit files (if not already in output_files)
                    for filename in state.audit_files:
                        if filename not in state.output_files:
                            filepath = Path("/app/outputs") / filename
                            if filepath.exists():
                                try:
                                    filepath.unlink()
                                    deleted_files += 1
                                    self.logger.info(f"Deleted audit file: {filename}")
                                except Exception as e:
                                    self.logger.error(f"Failed to delete {filename}: {e}")
                
                # Delete persisted state file
                state_file = self.persistence_dir / f"{exec_id}.json"
                if state_file.exists():
                    try:
                        state_file.unlink()
                        self.logger.info(f"Deleted state file: {state_file.name}")
                    except Exception as e:
                        self.logger.error(f"Failed to delete state file {state_file}: {e}")
                
                # Remove from memory
                del self._executions[exec_id]
                deleted_count += 1
            
            self.logger.info(
                f"Cleanup complete: Deleted {deleted_count} executions "
                f"and {deleted_files} files. {len(self._executions)} executions remaining."
            )
            
            return {
                "deleted_executions": deleted_count,
                "deleted_files": deleted_files,
                "remaining_executions": len(self._executions)
            }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        async with self._lock:
            return {
                **self._stats,
                "current_queue_length": len(self._queue),
                "current_active_count": len(self._active),
                "total_stored_executions": len(self._executions)
            }
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution (remove from queue or mark for cancellation)."""
        async with self._lock:
            if execution_id not in self._executions:
                return False
            
            execution = self._executions[execution_id]
            
            if execution.status == ExecutionStatus.QUEUED:
                # Remove from queue
                if execution_id in self._queue:
                    self._queue.remove(execution_id)
                
                # Update queue positions
                for i, queued_id in enumerate(self._queue):
                    self._executions[queued_id].queue_position = i + 1
                
                execution.status = ExecutionStatus.CANCELLED
                execution.end_time = datetime.now()
                self._stats["cancelled_executions"] += 1
                
                self.logger.info(f"Cancelled queued execution {execution_id}")
                return True
            
            elif execution.status in [ExecutionStatus.STARTING, ExecutionStatus.RUNNING]:
                # Mark for cancellation (actual cancellation handled by executor)
                self._cancellation_signals[execution_id] = True
                execution.status = ExecutionStatus.CANCELLED
                self.logger.info(f"Marked execution {execution_id} for cancellation")
                return True
            
            return False
    
    def request_cancellation(self, execution_id: str):
        """Signal that execution should be cancelled (synchronous version for non-async contexts)."""
        self._cancellation_signals[execution_id] = True
        if execution_id in self._executions:
            self.logger.info(f"Cancellation requested for execution {execution_id}")
    
    def is_cancelled(self, execution_id: str) -> bool:
        """Check if execution has been cancelled."""
        return self._cancellation_signals.get(execution_id, False)
    
    def mark_cancelled(self, execution_id: str):
        """Mark execution as cancelled and clean up cancellation signal."""
        if execution_id in self._cancellation_signals:
            self._cancellation_signals.pop(execution_id, None)
        self.logger.info(f"Execution {execution_id} marked as cancelled")
    
    def check_should_abort(self, execution_id: str):
        """
        Check if execution should abort.
        Raises CancellationError if cancelled.
        
        This should be called periodically during long-running operations.
        """
        if self.is_cancelled(execution_id):
            raise asyncio.CancelledError(f"Execution {execution_id} was cancelled")
    
    async def get_all_executions(self, limit: int = 100) -> List[ExecutionState]:
        """Get all executions (for admin/debugging purposes)."""
        async with self._lock:
            executions = list(self._executions.values())
            # Sort by start time (newest first)
            executions.sort(key=lambda x: x.start_time, reverse=True)
            return executions[:limit]
    
    def _save_to_disk(self, execution_id: str):
        """Save execution state to disk for persistence."""
        try:
            execution = self._executions.get(execution_id)
            if not execution:
                return
            
            # Convert to dict for JSON serialization
            data = {
                "execution_id": execution.execution_id,
                "command": execution.command,
                "args": execution.args,
                "status": execution.status.value,
                "start_time": execution.start_time.isoformat(),
                "end_time": execution.end_time.isoformat() if execution.end_time else None,
                "error_message": execution.error_message,
                "return_code": execution.return_code,
                "queue_position": execution.queue_position,
                "gamma_metadata": execution.gamma_metadata,  # Include Gamma metadata
                "audit_files": execution.audit_files,  # Include audit files
                "output_files": execution.output_files,  # Include output files
                "output_count": len(list(execution.output_buffer)) if execution.output_buffer else 0
            }
            
            # Save to file
            filepath = self.persistence_dir / f"{execution_id}.json"
            import json
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save execution {execution_id} to disk: {e}")
    
    def _load_from_disk(self):
        """Load existing executions from disk on startup."""
        try:
            if not self.persistence_dir.exists():
                return
            
            import json
            from collections import deque
            
            loaded_count = 0
            for filepath in self.persistence_dir.glob("*.json"):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    # Recreate ExecutionState
                    execution = ExecutionState(
                        execution_id=data["execution_id"],
                        command=data["command"],
                        args=data["args"],
                        status=ExecutionStatus(data["status"]),
                        start_time=datetime.fromisoformat(data["start_time"]),
                        end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
                        output_buffer=deque(maxlen=1000),  # Empty buffer on reload
                        error_message=data.get("error_message"),
                        return_code=data.get("return_code"),
                        queue_position=data.get("queue_position"),
                        gamma_metadata=data.get("gamma_metadata"),  # Load Gamma metadata
                        audit_files=data.get("audit_files", []),  # Load audit files
                        output_files=data.get("output_files", [])  # Load output files
                    )
                    
                    self._executions[execution.execution_id] = execution
                    loaded_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to load execution from {filepath}: {e}")
            
            if loaded_count > 0:
                self.logger.info(f"Loaded {loaded_count} executions from disk")
                
        except Exception as e:
            self.logger.error(f"Failed to load executions from disk: {e}")
    
    async def update_gamma_metadata(self, execution_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update Gamma metadata for an execution.
        
        Args:
            execution_id: The execution ID to update
            metadata: Gamma metadata dictionary
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            async with self._lock:
                execution = self._executions.get(execution_id)
                if not execution:
                    self.logger.warning(f"Execution {execution_id} not found for gamma metadata update")
                    return False
                
                # Validate metadata structure
                if not isinstance(metadata, dict):
                    self.logger.error(f"Invalid gamma metadata type: {type(metadata)}")
                    return False
                
                execution.gamma_metadata = metadata
                self._save_to_disk(execution_id)
                
                self.logger.info(
                    "gamma_metadata_updated",
                    execution_id=execution_id,
                    metadata_keys=list(metadata.keys())
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update gamma metadata for {execution_id}: {e}")
            return False
