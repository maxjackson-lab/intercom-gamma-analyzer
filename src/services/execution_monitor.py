"""
Execution Monitor - Production-Grade Execution Tracking

Provides persistent storage, agent-level tracking, and real-time status updates
for the multi-agent analysis system.

Inspired by: Vercel build logs, LangSmith traces, Railway deployments
"""

import sqlite3
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field, asdict
import uuid

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Overall execution status"""
    INITIALIZING = "initializing"
    EXTRACTING_DATA = "extracting_data"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(Enum):
    """Individual agent status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentExecution:
    """Tracks execution of a single agent"""
    name: str
    status: AgentStatus = AgentStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error_message: Optional[str] = None
    token_usage: Dict[str, int] = field(default_factory=dict)
    cost: Optional[float] = None
    confidence: Optional[float] = None
    
    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "error_message": self.error_message,
            "token_usage": self.token_usage,
            "cost": self.cost,
            "confidence": self.confidence
        }


@dataclass
class ExecutionRun:
    """Complete execution run with all agents and metadata"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    status: ExecutionStatus = ExecutionStatus.INITIALIZING
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Configuration
    command: str = ""
    args: List[str] = field(default_factory=list)
    date_range: Dict[str, str] = field(default_factory=dict)
    conversations_count: int = 0
    sample_size: Optional[int] = None
    
    # Progress tracking
    current_phase: str = "Initializing"
    current_agent: Optional[str] = None
    progress_percentage: float = 0.0
    
    # Agent tracking
    agents: List[AgentExecution] = field(default_factory=list)
    agent_order: List[str] = field(default_factory=list)
    
    # Results
    gamma_url: Optional[str] = None
    output_files: List[Dict[str, str]] = field(default_factory=list)
    summary_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Errors and warnings
    errors: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[Dict[str, str]] = field(default_factory=list)
    
    # Cost tracking
    total_cost: float = 0.0
    total_tokens: Dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "command": self.command,
            "args": self.args,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "date_range": self.date_range,
            "conversations_count": self.conversations_count,
            "current_phase": self.current_phase,
            "current_agent": self.current_agent,
            "progress_percentage": self.progress_percentage,
            "agents": [a.to_dict() for a in self.agents],
            "gamma_url": self.gamma_url,
            "output_files": self.output_files,
            "summary_stats": self.summary_stats,
            "errors": self.errors,
            "warnings": self.warnings,
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens
        }


class ExecutionStore:
    """
    Persistent storage for execution runs using SQLite.
    
    Survives Railway redeploys by using persistent volume mount.
    Compatible with Railway's /mnt/persistent/ pattern.
    """
    
    def __init__(self, db_path: str = "/app/outputs/executions.db"):
        """
        Initialize execution store.
        
        Args:
            db_path: Path to SQLite database
                    Default: /app/outputs/executions.db (ephemeral but same as other outputs)
                    For persistence: Set EXECUTION_DB_PATH=/mnt/persistent/executions.db
        """
        import os
        db_path = os.getenv('EXECUTION_DB_PATH', db_path)
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        self._init_db()
        self.logger.info(f"ExecutionStore initialized: {self.db_path}")
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Execution runs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_runs (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    command TEXT,
                    args TEXT,
                    status TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    date_range TEXT,
                    conversations_count INTEGER,
                    current_phase TEXT,
                    progress_percentage REAL,
                    gamma_url TEXT,
                    summary_stats TEXT,
                    total_cost REAL,
                    total_tokens TEXT,
                    data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Agent executions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    agent_name TEXT,
                    status TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_seconds REAL,
                    input_summary TEXT,
                    output_summary TEXT,
                    token_usage TEXT,
                    cost REAL,
                    confidence REAL,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (run_id) REFERENCES execution_runs(id)
                )
            """)
            
            # Create indexes for fast queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON execution_runs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_started ON execution_runs(started_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agents_run ON agent_executions(run_id)")
            
            self.logger.info("Database schema initialized")
    
    def save_run(self, run: ExecutionRun):
        """Save or update execution run"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO execution_runs 
                (id, name, command, args, status, started_at, completed_at, 
                 date_range, conversations_count, current_phase, progress_percentage,
                 gamma_url, summary_stats, total_cost, total_tokens, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.id,
                run.name,
                run.command,
                json.dumps(run.args),
                run.status.value,
                run.started_at.isoformat(),
                run.completed_at.isoformat() if run.completed_at else None,
                json.dumps(run.date_range),
                run.conversations_count,
                run.current_phase,
                run.progress_percentage,
                run.gamma_url,
                json.dumps(run.summary_stats),
                run.total_cost,
                json.dumps(run.total_tokens),
                json.dumps(run.to_dict())
            ))
            
            # Save agent executions
            for agent in run.agents:
                self._save_agent(conn, run.id, agent)
    
    def _save_agent(self, conn, run_id: str, agent: AgentExecution):
        """Save or update agent execution"""
        conn.execute("""
            INSERT OR REPLACE INTO agent_executions
            (run_id, agent_name, status, started_at, completed_at, duration_seconds,
             input_summary, output_summary, token_usage, cost, confidence, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            agent.name,
            agent.status.value,
            agent.started_at.isoformat() if agent.started_at else None,
            agent.completed_at.isoformat() if agent.completed_at else None,
            agent.duration_seconds,
            agent.input_summary,
            agent.output_summary,
            json.dumps(agent.token_usage),
            agent.cost,
            agent.confidence,
            agent.error_message
        ))
    
    def get_run(self, run_id: str) -> Optional[Dict]:
        """Get execution run by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM execution_runs WHERE id = ?
            """, (run_id,)).fetchone()
            
            if row:
                run_dict = dict(row)
                # Load agents
                agents = self.get_run_agents(run_id)
                run_dict['agents'] = agents
                return run_dict
            return None
    
    def get_run_agents(self, run_id: str) -> List[Dict]:
        """Get all agent executions for a run"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM agent_executions 
                WHERE run_id = ?
                ORDER BY id ASC
            """, (run_id,)).fetchall()
            return [dict(row) for row in rows]
    
    def get_recent_runs(self, limit: int = 50, status: Optional[str] = None) -> List[Dict]:
        """Get recent execution runs"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if status:
                rows = conn.execute("""
                    SELECT * FROM execution_runs 
                    WHERE status = ?
                    ORDER BY started_at DESC 
                    LIMIT ?
                """, (status, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM execution_runs 
                    ORDER BY started_at DESC 
                    LIMIT ?
                """, (limit,)).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict:
        """Get execution statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_runs,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(total_cost) as avg_cost,
                    SUM(total_cost) as total_cost
                FROM execution_runs
            """).fetchone()
            
            return dict(stats) if stats else {}


class ExecutionMonitor:
    """
    Centralized execution monitoring with real-time updates.
    
    Features:
    - Persistent storage (SQLite)
    - Real-time SSE broadcasting
    - Agent-level tracking
    - Cost/token aggregation
    - File and Gamma URL management
    """
    
    def __init__(self, store: ExecutionStore = None):
        self.store = store or ExecutionStore()
        self.current_run: Optional[ExecutionRun] = None
        self.listeners: List[asyncio.Queue] = []
        self.logger = logging.getLogger(__name__)
        
        # Agent execution order (for progress calculation)
        self.default_agent_order = [
            "SegmentationAgent",
            "TopicDetectionAgent",
            "SubTopicDetectionAgent",
            "TopicSentimentAgent",
            "ExampleExtractionAgent",
            "FinPerformanceAgent",
            "CorrelationAgent",
            "QualityInsightsAgent",
            "ChurnRiskAgent",
            "ConfidenceMetaAgent",
            "TrendAgent",
            "OutputFormatterAgent"
        ]
    
    async def start_execution(
        self, 
        command: str,
        args: List[str],
        date_range: Optional[Dict] = None,
        conversations_count: int = 0
    ) -> str:
        """
        Start a new execution run.
        
        Returns:
            run_id: Unique execution ID
        """
        self.current_run = ExecutionRun(
            name=f"{command} {date_range.get('start', '')} to {date_range.get('end', '')}" if date_range else command,
            command=command,
            args=args,
            date_range=date_range or {},
            conversations_count=conversations_count,
            agent_order=self.default_agent_order.copy()
        )
        
        # Initialize agent placeholders
        for agent_name in self.default_agent_order:
            self.current_run.agents.append(AgentExecution(name=agent_name))
        
        # Persist immediately
        self.store.save_run(self.current_run)
        
        # Broadcast to listeners
        await self.broadcast({
            "type": "execution_started",
            "run_id": self.current_run.id,
            "name": self.current_run.name,
            "conversations_count": conversations_count,
            "message": f"Started: {self.current_run.name}"
        })
        
        self.logger.info(f"Started execution: {self.current_run.id} - {self.current_run.name}")
        return self.current_run.id
    
    async def update_agent_status(
        self, 
        agent_name: str, 
        status: AgentStatus,
        message: str = "",
        confidence: Optional[float] = None,
        token_usage: Optional[Dict[str, int]] = None,
        cost: Optional[float] = None,
        **kwargs
    ):
        """
        Update status of a specific agent.
        
        Args:
            agent_name: Name of the agent
            status: New status
            message: Status message
            **kwargs: Additional fields (token_usage, cost, confidence, etc.)
        """
        if not self.current_run:
            self.logger.warning(f"No current run - cannot update agent {agent_name}")
            return
        
        # Find agent
        agent_exec = next((a for a in self.current_run.agents if a.name == agent_name), None)
        if not agent_exec:
            # Create new agent execution if not in default list
            agent_exec = AgentExecution(name=agent_name)
            self.current_run.agents.append(agent_exec)
        
        # Update status
        agent_exec.status = status
        
        if status == AgentStatus.RUNNING:
            agent_exec.started_at = datetime.now()
            self.current_run.current_agent = agent_name
        elif status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.SKIPPED]:
            agent_exec.completed_at = datetime.now()
            if agent_exec.started_at:
                agent_exec.duration_seconds = (agent_exec.completed_at - agent_exec.started_at).total_seconds()
        
        # Update additional fields
        if confidence is not None:
            agent_exec.confidence = confidence
        if token_usage:
            agent_exec.token_usage.update(token_usage)
        if cost is not None:
            agent_exec.cost = cost
        for key, value in kwargs.items():
            if hasattr(agent_exec, key):
                setattr(agent_exec, key, value)
        
        # Update aggregates
        if status == AgentStatus.COMPLETED and agent_exec.token_usage:
            for token_type, count in agent_exec.token_usage.items():
                self.current_run.total_tokens[token_type] = self.current_run.total_tokens.get(token_type, 0) + count
        
        if status == AgentStatus.COMPLETED and agent_exec.cost:
            self.current_run.total_cost += agent_exec.cost
        
        # Calculate progress
        completed_agents = len([a for a in self.current_run.agents if a.status == AgentStatus.COMPLETED])
        total_agents = len(self.current_run.agent_order)
        self.current_run.progress_percentage = (completed_agents / total_agents * 100) if total_agents > 0 else 0
        
        # Persist
        self.store.save_run(self.current_run)
        
        # Broadcast
        await self.broadcast({
            "type": "agent_update",
            "agent": agent_name,
            "status": status.value,
            "message": message,
            "progress": self.current_run.progress_percentage,
            "duration": agent_exec.duration_seconds,
            "cost": agent_exec.cost,
            "tokens": agent_exec.token_usage,
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.info(f"Agent {agent_name}: {status.value} - {message}")
    
    async def update_phase(self, phase: str, status: Optional[ExecutionStatus] = None):
        """Update current execution phase"""
        if not self.current_run:
            return
        
        self.current_run.current_phase = phase
        if status:
            self.current_run.status = status
        
        self.store.save_run(self.current_run)
        
        await self.broadcast({
            "type": "phase_update",
            "phase": phase,
            "status": status.value if status else None,
            "message": f"Phase: {phase}"
        })
    
    async def complete_execution(self, gamma_url: Optional[str] = None, summary_stats: Optional[Dict] = None):
        """Mark execution as completed"""
        if not self.current_run:
            return
        
        self.current_run.status = ExecutionStatus.COMPLETED
        self.current_run.completed_at = datetime.now()
        self.current_run.progress_percentage = 100.0
        
        if gamma_url:
            self.current_run.gamma_url = gamma_url
        if summary_stats:
            self.current_run.summary_stats = summary_stats
        
        duration = (self.current_run.completed_at - self.current_run.started_at).total_seconds()
        
        self.store.save_run(self.current_run)
        
        await self.broadcast({
            "type": "execution_completed",
            "run_id": self.current_run.id,
            "duration_seconds": duration,
            "gamma_url": gamma_url,
            "total_cost": self.current_run.total_cost,
            "message": f"✓ Completed successfully in {duration:.1f}s"
        })
        
        self.logger.info(f"Execution completed: {self.current_run.id} in {duration:.1f}s")
    
    async def fail_execution(self, error_message: str):
        """Mark execution as failed"""
        if not self.current_run:
            return
        
        self.current_run.status = ExecutionStatus.FAILED
        self.current_run.completed_at = datetime.now()
        self.current_run.errors.append({
            "timestamp": datetime.now().isoformat(),
            "message": error_message
        })
        
        self.store.save_run(self.current_run)
        
        await self.broadcast({
            "type": "execution_failed",
            "run_id": self.current_run.id,
            "error": error_message,
            "message": f"✗ Execution failed: {error_message}"
        })
        
        self.logger.error(f"Execution failed: {self.current_run.id} - {error_message}")
    
    async def add_file(self, filename: str, path: str, file_type: str, size: int):
        """Track output file"""
        if not self.current_run:
            return
        
        file_info = {
            "filename": filename,
            "path": path,
            "type": file_type,
            "size": size,
            "created_at": datetime.now().isoformat()
        }
        
        self.current_run.output_files.append(file_info)
        self.store.save_run(self.current_run)
        
        await self.broadcast({
            "type": "file_created",
            "file": file_info,
            "message": f"Created: {filename}"
        })
    
    async def broadcast(self, message: dict):
        """Send message to all listening clients"""
        dead_queues = []
        for queue in self.listeners:
            try:
                await asyncio.wait_for(queue.put(message), timeout=1.0)
            except (asyncio.TimeoutError, Exception):
                dead_queues.append(queue)
        
        # Clean up dead connections
        for queue in dead_queues:
            self.listeners.remove(queue)
    
    async def stream_updates(self):
        """SSE generator for real-time updates"""
        queue = asyncio.Queue(maxsize=100)
        self.listeners.append(queue)
        
        try:
            # Send current state immediately
            if self.current_run:
                yield f"data: {json.dumps({'type': 'current_state', 'run': self.current_run.to_dict()})}\n\n"
            
            # Stream updates
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive
                    yield f": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in self.listeners:
                self.listeners.remove(queue)


# Global instance (singleton pattern for web server)
_monitor_instance: Optional[ExecutionMonitor] = None

def get_execution_monitor() -> ExecutionMonitor:
    """Get or create global execution monitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ExecutionMonitor()
    return _monitor_instance

