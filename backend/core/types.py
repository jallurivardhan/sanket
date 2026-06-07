import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

class SignalType(str, Enum):
    FRAUD_PATTERN = "FRAUD_PATTERN"
    SYNTHETIC_IDENTITY = "SYNTHETIC_IDENTITY"
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"
    MONEY_LAUNDERING = "MONEY_LAUNDERING"
    COORDINATED_ATTACK = "COORDINATED_ATTACK"

class SignalSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AgentAction(str, Enum):
    FLAG_ACCOUNT = "FLAG_ACCOUNT"
    FREEZE_TRANSACTION = "FREEZE_TRANSACTION"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    REQUEST_VERIFICATION = "REQUEST_VERIFICATION"
    NO_ACTION = "NO_ACTION"

class AgentStatus(str, Enum):
    IDLE = "IDLE"
    MONITORING = "MONITORING"
    DETECTING = "DETECTING"
    TRANSMITTING = "TRANSMITTING"
    RECEIVING = "RECEIVING"
    ACTING = "ACTING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

class DemoScenario(str, Enum):
    COORDINATED_FRAUD = "COORDINATED_FRAUD"
    SYNTHETIC_IDENTITY = "SYNTHETIC_IDENTITY"
    NORMAL_BASELINE = "NORMAL_BASELINE"

class PrivacyPreservedSignal(BaseModel):
    signal_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the privacy-preserved signal"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of when the signal was generated"
    )
    signal_type: SignalType = Field(
        ...,
        description="Categorical type of fraud signal detected"
    )
    severity: SignalSeverity = Field(
        ...,
        description="Severity level of the detected potential fraud"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score of the fraud detection model (0.0 to 1.0)"
    )
    behavioral_fingerprint: Dict[str, Any] = Field(
        ...,
        description="Anonymized behavioral pattern data (velocity, amount, timing) with zero raw PII"
    )
    pattern_hash: str = Field(
        ...,
        description="SHA-256 hash of the behavioral fingerprint for verification"
    )
    geographic_region: str = Field(
        ...,
        description="Anonymized geographic region (country/state/province only)"
    )
    transaction_velocity: float = Field(
        ...,
        description="Transaction frequency velocity measured in transactions per hour"
    )
    amount_percentile: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="The percentile of the transaction amount relative to typical institutional volume"
    )
    originating_institution_id: str = Field(
        ...,
        description="Hashed unique identifier of the institution that detected and sent the signal"
    )
    target_institution_ids: List[str] = Field(
        ...,
        description="List of hashed institution identifiers destined to receive the signal"
    )
    regulatory_basis: str = Field(
        ...,
        description="Specific regulatory framework or law justifying the sharing of this signal"
    )
    requires_sar: bool = Field(
        ...,
        description="Flag indicating if a Suspicious Activity Report (SAR) filing is required or recommended"
    )

    @field_validator('behavioral_fingerprint')
    @classmethod
    def validate_no_pii(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if v is None:
            return v
        pii_keys = {'name', 'ssn', 'account_number', 'card_number', 'email', 'phone', 'address', 'dob', 'passport'}
        for key in v.keys():
            if key.lower() in pii_keys:
                raise ValueError(f"PII key '{key}' is not allowed in behavioral_fingerprint")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "signal_id": "4e72322c-a25e-4efd-b94d-c19eb502be8e",
                    "timestamp": "2026-06-07T21:48:41Z",
                    "signal_type": "COORDINATED_ATTACK",
                    "severity": "HIGH",
                    "confidence_score": 0.92,
                    "behavioral_fingerprint": {
                        "velocity_5m": 12,
                        "avg_amount_usd": 4500.0,
                        "device_switches": 3
                    },
                    "pattern_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "geographic_region": "US-NY",
                    "transaction_velocity": 144.0,
                    "amount_percentile": 0.98,
                    "originating_institution_id": "8af1593cde43",
                    "target_institution_ids": ["f3089d87c112"],
                    "regulatory_basis": "Bank Secrecy Act Section 314(b)",
                    "requires_sar": True
                }
            ]
        }
    }

class AgentState(BaseModel):
    institution_id: str = Field(
        ...,
        description="Hashed unique identifier of the institution associated with this state"
    )
    institution_name: str = Field(
        ...,
        description="Friendly name of the institution for local agent reference"
    )
    agent_id: str = Field(
        ...,
        description="Unique identifier of the AI agent executing the LangGraph process"
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier of the current collaborative detection session"
    )
    status: AgentStatus = Field(
        default=AgentStatus.IDLE,
        description="Current workflow status of the AI agent"
    )
    raw_transactions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Raw local transactions being analyzed. MUST remain local and never be transmitted."
    )
    detected_patterns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of detected anomalies or suspicious transaction patterns"
    )
    signals_to_send: List[PrivacyPreservedSignal] = Field(
        default_factory=list,
        description="Privacy-preserved signals generated during analysis ready to be broadcast"
    )
    signals_received: List[PrivacyPreservedSignal] = Field(
        default_factory=list,
        description="Signals received from other institutions to correlate with local events"
    )
    actions_taken: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Actions taken by the agent as a result of the correlation/detection"
    )
    accounts_flagged: List[str] = Field(
        default_factory=list,
        description="Hashed account identifiers flagged for suspicious activity"
    )
    audit_trail: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Chronological log of agent actions and state transitions"
    )
    arize_trace_id: Optional[str] = Field(
        default=None,
        description="Arize Phoenix trace identifier for system observability"
    )
    gemini_reasoning: Optional[str] = Field(
        default=None,
        description="Detailed plain text reasoning output by the Gemini 3.1 Pro model"
    )
    confidence_threshold: float = Field(
        default=0.85,
        description="Minimum confidence score threshold required to trigger automated action"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the agent encountered a failure in processing"
    )
    completed: bool = Field(
        default=False,
        description="Flag indicating if the agent workflow execution has finished"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of when this agent state session was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the last update to this agent state"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "institution_id": "8af1593cde43",
                    "institution_name": "Apex Bank",
                    "agent_id": "apex-fraud-agent-01",
                    "session_id": "6c459f20-21a4-4df8-927c-9b1b4c9e99c8",
                    "status": "MONITORING",
                    "raw_transactions": [
                        {"tx_id": "tx_123", "amount": 12000.0, "timestamp": "2026-06-07T17:00:00Z"}
                    ],
                    "detected_patterns": [
                        {"pattern": "velocity_spike", "score": 0.89}
                    ],
                    "signals_to_send": [],
                    "signals_received": [],
                    "actions_taken": [],
                    "accounts_flagged": ["e3b0c44298fc"],
                    "audit_trail": [
                        {"action": "initialize", "timestamp": "2026-06-07T17:48:41Z"}
                    ],
                    "arize_trace_id": "tr_9a8b7c6d5e",
                    "gemini_reasoning": "Detected anomalous velocity spike exceeding standard regional thresholds.",
                    "confidence_threshold": 0.85,
                    "error": None,
                    "completed": False,
                    "created_at": "2026-06-07T17:48:41Z",
                    "updated_at": "2026-06-07T17:48:41Z"
                }
            ]
        }
    }

class Institution(BaseModel):
    institution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the participating institution"
    )
    name: str = Field(
        ...,
        description="Legal name of the institution"
    )
    institution_hash: str = Field(
        ...,
        description="SHA-256 hash of the institution_id used in shared network signals"
    )
    tier: str = Field(
        ...,
        description="The operational tier of the institution (regional, national, global)"
    )
    connected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the institution joined the Sanket network"
    )
    is_active: bool = Field(
        default=True,
        description="Active status of the institution on the signal network"
    )
    signal_count_sent: int = Field(
        default=0,
        description="Total number of privacy-preserved signals sent by this institution"
    )
    signal_count_received: int = Field(
        default=0,
        description="Total number of privacy-preserved signals received by this institution"
    )
    fraud_prevented_usd: float = Field(
        default=0.0,
        description="Estimated USD amount of fraud prevented by using the network signals"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "institution_id": "f3089d87c112",
                    "name": "Apex Bank",
                    "institution_hash": "8af1593cde431234567890abcdef",
                    "tier": "national",
                    "connected_at": "2026-06-07T17:48:41Z",
                    "is_active": True,
                    "signal_count_sent": 150,
                    "signal_count_received": 340,
                    "fraud_prevented_usd": 1250000.00
                }
            ]
        }
    }

class AuditEntry(BaseModel):
    entry_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this immutable audit log entry"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the audited event"
    )
    institution_id: str = Field(
        ...,
        description="Identifier of the institution performing the action"
    )
    agent_id: str = Field(
        ...,
        description="Identifier of the AI agent performing the action"
    )
    event_type: str = Field(
        ...,
        description="Type of event recorded (e.g., signal_generated, signal_received, action_executed)"
    )
    signal_id: Optional[str] = Field(
        default=None,
        description="Optional unique identifier of the related privacy-preserved signal"
    )
    action_taken: Optional[AgentAction] = Field(
        default=None,
        description="Optional action taken by the AI agent in response to the event"
    )
    reasoning: str = Field(
        ...,
        description="Plain English explanation of the decision or recommendation made"
    )
    confidence: float = Field(
        ...,
        description="Confidence score supporting the audited decision"
    )
    regulatory_basis: Optional[str] = Field(
        default=None,
        description="Applicable law or compliance statute supporting the sharing/action (e.g. BSA Section 314(b))"
    )
    arize_span_id: Optional[str] = Field(
        default=None,
        description="Arize Phoenix execution span ID to trace the LLM decision-making process"
    )
    previous_entry_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of the previous audit log entry to establish an immutable audit chain"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "entry_id": "7b8f9e0d-1234-5678-abcd-ef0123456789",
                    "timestamp": "2026-06-07T17:48:41Z",
                    "institution_id": "8af1593cde43",
                    "agent_id": "apex-fraud-agent-01",
                    "event_type": "ACTION_EXECUTED",
                    "signal_id": "4e72322c-a25e-4efd-b94d-c19eb502be8e",
                    "action_taken": "FREEZE_TRANSACTION",
                    "reasoning": "Coordinated attack detected across multiple regional banks. Local transaction frozen to prevent imminent loss.",
                    "confidence": 0.96,
                    "regulatory_basis": "Bank Secrecy Act Section 314(b)",
                    "arize_span_id": "sp_4a5b6c7d8e",
                    "previous_entry_hash": "a4d3c2b1a4d3c2b1a4d3c2b1a4d3c2b1a4d3c2b1a4d3c2b1a4d3c2b1a4d3c2b1"
                }
            ]
        }
    }

class NetworkStats(BaseModel):
    institutions_connected: int = Field(
        ...,
        description="Total number of active financial institutions connected to the Sanket network"
    )
    signals_routed_total: int = Field(
        ...,
        description="Cumulative count of all signals routed across the network since launch"
    )
    avg_routing_time_ms: float = Field(
        ...,
        description="Average latency for signal routing across the network, in milliseconds"
    )
    network_uptime_pct: float = Field(
        ...,
        description="The percentage uptime of the Sanket network infrastructure"
    )
    fraud_prevented_usd: float = Field(
        ...,
        description="Total estimated volume of financial fraud prevented in USD across the network"
    )
    last_signal_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the most recent signal routed"
    )
    active_alerts: int = Field(
        ...,
        description="Number of critical alerts currently active and unresolved in the network"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "institutions_connected": 12,
                    "signals_routed_total": 4582,
                    "avg_routing_time_ms": 284.5,
                    "network_uptime_pct": 99.98,
                    "fraud_prevented_usd": 15450000.00,
                    "last_signal_at": "2026-06-07T17:48:41Z",
                    "active_alerts": 3
                }
            ]
        }
    }
