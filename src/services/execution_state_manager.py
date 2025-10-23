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
    
    async def cleanup_old_executions(self, max_age_hours: int = 1):
        """Clean up old completed executions."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        async with self._lock:
            to_remove = []
            for execution_id, execution in self._executions.items():
                if (execution.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, 
                                       ExecutionStatus.CANCELLED, ExecutionStatus.TIMEOUT, ExecutionStatus.ERROR] and
                    execution.end_time and execution.end_time < cutoff_time):
                    to_remove.append(execution_id)
            
            for execution_id in to_remove:
                del self._executions[execution_id]
            
            if to_remove:
                self.logger.info(f"Cleaned up {len(to_remove)} old executions")
    
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
                execution.status = ExecutionStatus.CANCELLED
                self.logger.info(f"Marked execution {execution_id} for cancellation")
                return True
            
            return False
    
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
                        gamma_metadata=data.get("gamma_metadata")  # Load Gamma metadata
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
