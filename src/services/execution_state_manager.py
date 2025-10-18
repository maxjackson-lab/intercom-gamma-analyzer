"""
Execution State Manager

Manages in-memory state for web command executions, including
tracking active executions, queuing, and cleanup.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
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
    """Execution state data structure."""
    execution_id: str
    command: str
    args: List[str]
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    output_buffer: List[Dict[str, Any]] = None
    error_message: Optional[str] = None
    return_code: Optional[int] = None
    queue_position: Optional[int] = None
    
    def __post_init__(self):
        if self.output_buffer is None:
            self.output_buffer = []


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
    
    def __init__(self, max_concurrent: int = 5, max_queue_size: int = 20):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.logger = logging.getLogger(self.__class__.__name__)
        
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
