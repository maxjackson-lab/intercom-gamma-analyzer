"""
Human-in-the-Loop (HITL) controller for command approval workflows.

Implements risk-based approval requirements, audit logging,
and dynamic threshold adjustment for command execution.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval status for commands."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class RiskLevel(Enum):
    """Risk level for command execution."""
    LOW = "low"         # Auto-approve
    MEDIUM = "medium"   # Quick approval
    HIGH = "high"       # Detailed approval
    CRITICAL = "critical"  # Explicit confirmation


@dataclass
class ApprovalRequest:
    """Request for command approval."""
    request_id: str
    command: List[str]
    risk_level: RiskLevel
    risk_score: float
    explanation: str
    warnings: List[str]
    timestamp: datetime
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    denial_reason: Optional[str] = None


@dataclass
class ApprovalConfig:
    """Configuration for approval thresholds."""
    auto_approve_threshold: float = 2.0
    quick_approve_threshold: float = 5.0
    detailed_approve_threshold: float = 7.0
    max_pending_requests: int = 10
    request_timeout_minutes: int = 30


class HITLController:
    """
    Human-in-the-Loop controller for command approval.
    
    Implements risk-based approval workflows with:
    - Dynamic risk assessment
    - Configurable approval thresholds
    - Audit logging of all decisions
    - Request timeout handling
    """
    
    def __init__(self, config: Optional[ApprovalConfig] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or ApprovalConfig()
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.approval_history: List[ApprovalRequest] = []
        
        # Risk factors and their weights
        self.risk_factors = {
            "command_dangerous": 3.0,
            "file_modification": 2.5,
            "system_access": 2.0,
            "network_access": 1.5,
            "elevated_privileges": 3.5,
            "destructive_operation": 4.0,
            "unknown_command": 2.0,
            "excessive_args": 1.0,
            "suspicious_patterns": 2.5,
        }
    
    def should_require_approval(self, command: List[str], risk_score: float, 
                              warnings: List[str]) -> bool:
        """
        Determine if a command requires human approval.
        
        Args:
            command: The command to be executed
            risk_score: Calculated risk score (0-10)
            warnings: List of security warnings
            
        Returns:
            True if approval is required
        """
        # Always require approval for critical risk
        if risk_score >= self.config.detailed_approve_threshold:
            return True
        
        # Check for specific risk factors
        command_text = " ".join(command).lower()
        
        # Check for destructive operations
        destructive_keywords = ["delete", "remove", "rm", "del", "format", "wipe"]
        if any(keyword in command_text for keyword in destructive_keywords):
            return True
        
        # Check for system modifications
        system_keywords = ["chmod", "chown", "sudo", "su", "install", "uninstall"]
        if any(keyword in command_text for keyword in system_keywords):
            return True
        
        # Check for network operations
        network_keywords = ["wget", "curl", "nc", "ssh", "scp", "rsync"]
        if any(keyword in command_text for keyword in network_keywords):
            return True
        
        # Check for file modifications
        file_keywords = ["write", "create", "modify", "update", "overwrite"]
        if any(keyword in command_text for keyword in file_keywords):
            return True
        
        # Require approval if there are warnings
        if warnings:
            return True
        
        return False
    
    def create_approval_request(self, command: List[str], risk_score: float,
                              explanation: str, warnings: List[str]) -> ApprovalRequest:
        """
        Create a new approval request.
        
        Args:
            command: The command to be executed
            risk_score: Calculated risk score
            explanation: Human-readable explanation
            warnings: List of security warnings
            
        Returns:
            ApprovalRequest object
        """
        request_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.pending_requests)}"
        
        # Determine risk level
        if risk_score >= self.config.detailed_approve_threshold:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= self.config.quick_approve_threshold:
            risk_level = RiskLevel.HIGH
        elif risk_score >= self.config.auto_approve_threshold:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        request = ApprovalRequest(
            request_id=request_id,
            command=command,
            risk_level=risk_level,
            risk_score=risk_score,
            explanation=explanation,
            warnings=warnings,
            timestamp=datetime.now()
        )
        
        self.pending_requests[request_id] = request
        self.logger.info(f"Created approval request {request_id} with risk level {risk_level.value}")
        
        return request
    
    def approve_request(self, request_id: str, approved_by: str) -> bool:
        """
        Approve a pending request.
        
        Args:
            request_id: ID of the request to approve
            approved_by: Identifier of the person approving
            
        Returns:
            True if approval was successful
        """
        if request_id not in self.pending_requests:
            self.logger.warning(f"Approval request {request_id} not found")
            return False
        
        request = self.pending_requests[request_id]
        request.status = ApprovalStatus.APPROVED
        request.approved_by = approved_by
        request.approval_timestamp = datetime.now()
        
        # Move to history
        self.approval_history.append(request)
        del self.pending_requests[request_id]
        
        self.logger.info(f"Request {request_id} approved by {approved_by}")
        return True
    
    def deny_request(self, request_id: str, reason: str) -> bool:
        """
        Deny a pending request.
        
        Args:
            request_id: ID of the request to deny
            reason: Reason for denial
            
        Returns:
            True if denial was successful
        """
        if request_id not in self.pending_requests:
            self.logger.warning(f"Approval request {request_id} not found")
            return False
        
        request = self.pending_requests[request_id]
        request.status = ApprovalStatus.DENIED
        request.denial_reason = reason
        request.approval_timestamp = datetime.now()
        
        # Move to history
        self.approval_history.append(request)
        del self.pending_requests[request_id]
        
        self.logger.info(f"Request {request_id} denied: {reason}")
        return True
    
    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        return list(self.pending_requests.values())
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a specific approval request."""
        return self.pending_requests.get(request_id)
    
    def cleanup_expired_requests(self) -> int:
        """
        Clean up expired requests.
        
        Returns:
            Number of requests cleaned up
        """
        now = datetime.now()
        expired_requests = []
        
        for request_id, request in self.pending_requests.items():
            time_diff = now - request.timestamp
            if time_diff.total_seconds() > (self.config.request_timeout_minutes * 60):
                expired_requests.append(request_id)
        
        for request_id in expired_requests:
            request = self.pending_requests[request_id]
            request.status = ApprovalStatus.EXPIRED
            request.approval_timestamp = now
            
            self.approval_history.append(request)
            del self.pending_requests[request_id]
            
            self.logger.info(f"Request {request_id} expired")
        
        return len(expired_requests)
    
    def get_approval_stats(self) -> Dict[str, Any]:
        """Get approval statistics."""
        total_requests = len(self.approval_history) + len(self.pending_requests)
        approved = len([r for r in self.approval_history if r.status == ApprovalStatus.APPROVED])
        denied = len([r for r in self.approval_history if r.status == ApprovalStatus.DENIED])
        expired = len([r for r in self.approval_history if r.status == ApprovalStatus.EXPIRED])
        pending = len(self.pending_requests)
        
        approval_rate = (approved / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "approved": approved,
            "denied": denied,
            "expired": expired,
            "pending": pending,
            "approval_rate": approval_rate,
            "risk_level_distribution": self._get_risk_distribution()
        }
    
    def _get_risk_distribution(self) -> Dict[str, int]:
        """Get distribution of risk levels in history."""
        distribution = {level.value: 0 for level in RiskLevel}
        
        for request in self.approval_history:
            distribution[request.risk_level.value] += 1
        
        return distribution
    
    def export_audit_log(self) -> str:
        """Export approval history as JSON for audit purposes."""
        audit_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_requests": len(self.approval_history),
            "requests": [asdict(request) for request in self.approval_history]
        }
        
        return json.dumps(audit_data, indent=2, default=str)
