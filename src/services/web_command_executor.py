"""
Web Command Executor Service

Handles real-time execution of CLI commands for the web interface,
streaming output via Server-Sent Events (SSE).
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, AsyncIterator, Any
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
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.active_processes: Dict[str, asyncio.subprocess.Process] = {}
        self.execution_states: Dict[str, Dict[str, Any]] = {}
        
    def generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        return str(uuid.uuid4())
    
    async def execute_command(
        self, 
        command: str, 
        args: List[str], 
        execution_id: Optional[str] = None,
        timeout: int = 1800  # 30 minutes default
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute a command and stream output in real-time.
        
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
            
        # Initialize execution state
        self.execution_states[execution_id] = {
            "status": "starting",
            "command": command,
            "args": args,
            "start_time": datetime.now(),
            "output_buffer": [],
            "process": None
        }
        
        try:
            # Yield start event
            yield {
                "type": "status",
                "data": f"Starting command: {command} {' '.join(args)}",
                "execution_id": execution_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                command, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/app",  # Railway container working directory
                env=settings.get_environment_variables()
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
                "timestamp": datetime.now().isoformat()
            }
            
            # Stream stdout
            async for line in process.stdout:
                line_data = line.decode('utf-8', errors='replace').rstrip()
                if line_data:  # Skip empty lines
                    # Buffer output for later download
                    self.execution_states[execution_id]["output_buffer"].append({
                        "type": "stdout",
                        "data": line_data,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    yield {
                        "type": "stdout",
                        "data": line_data,
                        "execution_id": execution_id,
                        "timestamp": datetime.now().isoformat()
                    }
            
            # Stream stderr
            async for line in process.stderr:
                line_data = line.decode('utf-8', errors='replace').rstrip()
                if line_data:  # Skip empty lines
                    # Buffer output for later download
                    self.execution_states[execution_id]["output_buffer"].append({
                        "type": "stderr",
                        "data": line_data,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    yield {
                        "type": "stderr",
                        "data": line_data,
                        "execution_id": execution_id,
                        "timestamp": datetime.now().isoformat()
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
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    self.execution_states[execution_id]["status"] = "failed"
                    yield {
                        "type": "error",
                        "data": f"Command failed with exit code: {return_code}",
                        "execution_id": execution_id,
                        "timestamp": datetime.now().isoformat()
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
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Command execution error: {e}")
            self.execution_states[execution_id]["status"] = "error"
            yield {
                "type": "error",
                "data": f"Execution error: {str(e)}",
                "execution_id": execution_id,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            # Cleanup
            if execution_id in self.active_processes:
                del self.active_processes[execution_id]
            
            # Update final state
            if execution_id in self.execution_states:
                self.execution_states[execution_id]["end_time"] = datetime.now()
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a running execution.
        
        Args:
            execution_id: The execution ID to cancel
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        if execution_id in self.active_processes:
            process = self.active_processes[execution_id]
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
                self.execution_states[execution_id]["status"] = "cancelled"
                self.logger.info(f"Execution {execution_id} cancelled successfully")
                return True
            except asyncio.TimeoutError:
                # Force kill if terminate doesn't work
                process.kill()
                await process.wait()
                self.execution_states[execution_id]["status"] = "force_killed"
                self.logger.warning(f"Execution {execution_id} force killed")
                return True
            except Exception as e:
                self.logger.error(f"Error cancelling execution {execution_id}: {e}")
                return False
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
        """Clean up old execution states."""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        to_remove = []
        for execution_id, state in self.execution_states.items():
            start_time = state.get("start_time", datetime.now())
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
