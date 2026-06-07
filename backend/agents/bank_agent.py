import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Wrapped import for ChatVertexAI
try:
    from langchain_google_vertexai import ChatVertexAI
    VERTEX_AI_AVAILABLE = True
except ImportError:
    ChatVertexAI = None
    VERTEX_AI_AVAILABLE = False

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from backend.core.types import (
    AgentState, AgentStatus, PrivacyPreservedSignal,
    SignalType, SignalSeverity, AgentAction, DemoScenario
)
from backend.utils.privacy import PrivacyFilter
from backend.utils.simulation import TransactionSimulator

class BankAgent:
    def __init__(
        self,
        institution_id: str,
        institution_name: str,
        gemini_model: str = "gemini-3.1-pro-preview"
    ):
        self.institution_id = institution_id
        self.institution_name = institution_name
        self.institution_hash = hashlib.sha256(institution_id.encode('utf-8')).hexdigest()[:16]
        self.privacy_filter = PrivacyFilter()
        self.logger = logging.getLogger(f"sanket.agent.{institution_name}")
        
        self.llm = None
        if VERTEX_AI_AVAILABLE and ChatVertexAI is not None:
            try:
                self.llm = ChatVertexAI(
                    model=gemini_model,
                    temperature=0.1,
                    max_tokens=2048,
                    convert_system_message_to_human=True
                )
            except Exception as e:
                self.logger.warning(f"Gemini not available, using mock reasoning: {e}")
        else:
            self.logger.warning("Gemini not available, using mock reasoning")

        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        """
        Build and compile the LangGraph StateGraph.
        """
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("monitor", self._node_monitor)
        workflow.add_node("analyze", self._node_analyze)
        workflow.add_node("strip_pii", self._node_strip_pii)
        workflow.add_node("prepare_signal", self._node_prepare_signal)
        workflow.add_node("process_received", self._node_process_received)
        workflow.add_node("execute_actions", self._node_execute_actions)
        workflow.add_node("audit", self._node_audit)
        
        # Set entry point
        workflow.set_entry_point("monitor")
        
        # Add edges
        workflow.add_edge("monitor", "analyze")
        
        # Conditional edge routing from analyze
        workflow.add_conditional_edges(
            "analyze",
            self._should_signal,
            {
                "signal": "strip_pii",
                "skip": "process_received"
            }
        )
        
        workflow.add_edge("strip_pii", "prepare_signal")
        workflow.add_edge("prepare_signal", "process_received")
        workflow.add_edge("process_received", "execute_actions")
        workflow.add_edge("execute_actions", "audit")
        workflow.add_edge("audit", END)
        
        return workflow.compile()

    # --- Nodes ---

    async def _node_monitor(self, state: Any) -> Dict[str, Any]:
        """
        Monitor node. Updates status and registers initial transaction scan event.
        """
        state_dict = state if isinstance(state, dict) else state.model_dump()
        state_dict["status"] = AgentStatus.MONITORING
        
        raw_txs = state_dict.get("raw_transactions", [])
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "monitoring_started",
            "transaction_count": len(raw_txs),
            "institution": self.institution_name
        }
        
        if state_dict.get("audit_trail") is None:
            state_dict["audit_trail"] = []
        state_dict["audit_trail"].append(audit_entry)
        
        return state_dict

    async def _node_analyze(self, state: Any) -> Dict[str, Any]:
        """
        Analyze node. Processes behavioral features using Gemini or mock algorithms.
        """
        state_dict = state if isinstance(state, dict) else state.model_dump()
        state_dict["status"] = AgentStatus.DETECTING
        
        raw_txs = state_dict.get("raw_transactions", [])
        if not raw_txs:
            return state_dict
            
        # Extract privacy-preserved summary
        behavioral = self.privacy_filter.extract_behavioral_only(raw_txs)
        
        detected = False
        decision = None
        
        if self.llm is not None:
            system_prompt = """You are a financial fraud detection AI agent 
for the Sanket network. You analyze behavioral 
patterns only — you never see customer PII.

Analyze the transaction patterns and respond 
ONLY with valid JSON in this exact format:
{
  "fraud_detected": true or false,
  "confidence": 0.0 to 1.0,
  "fraud_type": one of: fraud_pattern, synthetic_identity, account_takeover, money_laundering, coordinated_attack,
  "severity": one of: low, medium, high, critical,
  "reasoning": "plain English explanation under 100 words",
  "behavioral_indicators": {
    "velocity_anomaly": float,
    "amount_pattern": "description",
    "time_pattern": "description",
    "account_age_risk": "low/medium/high"
  },
  "regulatory_basis": "applicable regulation",
  "requires_sar": true or false
}
Respond ONLY with the JSON object. 
No markdown, no explanation."""
            
            human_message = f"Analyze these behavioral patterns:\n{json.dumps(behavioral, indent=2)}"
            
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_message)
                ]
                response = await self.llm.ainvoke(messages)
                resp_text = response.content
                
                # Strip Markdown block wraps if any
                cleaned_text = resp_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                elif cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()
                
                decision = json.loads(cleaned_text)
                detected = decision.get("fraud_detected", False)
            except Exception as e:
                self.logger.warning(f"Error during Gemini analysis: {e}. Falling back to mock.")
                decision = None
                
        if decision is None:
            # Fallback Mock logic
            risk_indicators = behavioral.get("risk_indicators", [])
            if len(risk_indicators) >= 3:
                decision = {
                    "fraud_detected": True,
                    "confidence": 0.87,
                    "fraud_type": "fraud_pattern",
                    "severity": "high",
                    "reasoning": f"Mock: Multiple risk indicators detected in behavioral patterns: {', '.join(risk_indicators[:2])}",
                    "behavioral_indicators": {
                        "velocity_anomaly": behavioral.get("velocity_per_hour", 0.0),
                        "amount_pattern": "unusual round sums",
                        "time_pattern": "burst activity",
                        "account_age_risk": "high" if behavioral.get("account_patterns", {}).get("new_account_ratio", 0.0) > 0.5 else "low"
                    },
                    "regulatory_basis": "BSA Section 5318(g)",
                    "requires_sar": True
                }
                detected = True
            else:
                decision = {
                    "fraud_detected": False,
                    "confidence": 0.1,
                    "fraud_type": "fraud_pattern",
                    "severity": "low",
                    "reasoning": "Mock: Baseline activity, no significant indicators.",
                    "behavioral_indicators": {},
                    "regulatory_basis": "",
                    "requires_sar": False
                }
                detected = False

        if detected and decision.get("confidence", 0.0) >= state_dict.get("confidence_threshold", 0.85):
            if state_dict.get("detected_patterns") is None:
                state_dict["detected_patterns"] = []
            state_dict["detected_patterns"].append(decision)
            
        state_dict["gemini_reasoning"] = decision.get("reasoning")
        return state_dict

    async def _node_strip_pii(self, state: Any) -> Dict[str, Any]:
        """
        Sanitize and strip any potential PII keys from detected patterns before sharing.
        """
        state_dict = state if isinstance(state, dict) else state.model_dump()
        state_dict["status"] = AgentStatus.TRANSMITTING
        
        patterns = state_dict.get("detected_patterns", [])
        sanitized_patterns = []
        
        for pat in patterns:
            sanitized = {
                "fraud_type": pat.get("fraud_type"),
                "severity": pat.get("severity"),
                "confidence": pat.get("confidence"),
                "behavioral_indicators": pat.get("behavioral_indicators"),
                "regulatory_basis": pat.get("regulatory_basis"),
                "requires_sar": pat.get("requires_sar")
            }
            sanitized_patterns.append(sanitized)
            
        state_dict["detected_patterns"] = sanitized_patterns
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "pii_stripped",
            "patterns_sanitized": len(sanitized_patterns)
        }
        if state_dict.get("audit_trail") is None:
            state_dict["audit_trail"] = []
        state_dict["audit_trail"].append(audit_entry)
        
        return state_dict

    async def _node_prepare_signal(self, state: Any) -> Dict[str, Any]:
        """
        Convert detected anomalies into PrivacyPreservedSignal objects.
        """
        state_dict = state if isinstance(state, dict) else state.model_dump()
        
        patterns = state_dict.get("detected_patterns", [])
        signals = []
        
        for pat in patterns:
            behavioral = pat.get("behavioral_indicators", {})
            fingerprint_str = json.dumps(behavioral, sort_keys=True)
            pattern_hash = hashlib.sha256(fingerprint_str.encode('utf-8')).hexdigest()
            
            # Map fraud type string to SignalType enum
            raw_type = str(pat.get("fraud_type", "")).upper().replace(" ", "_")
            try:
                sig_type = SignalType(raw_type)
            except ValueError:
                if "COORDINATED" in raw_type:
                    sig_type = SignalType.COORDINATED_ATTACK
                elif "SYNTHETIC" in raw_type:
                    sig_type = SignalType.SYNTHETIC_IDENTITY
                elif "TAKEOVER" in raw_type:
                    sig_type = SignalType.ACCOUNT_TAKEOVER
                elif "LAUNDERING" in raw_type:
                    sig_type = SignalType.MONEY_LAUNDERING
                else:
                    sig_type = SignalType.FRAUD_PATTERN
                    
            # Map severity string to SignalSeverity enum
            raw_sev = str(pat.get("severity", "")).upper()
            try:
                severity = SignalSeverity(raw_sev)
            except ValueError:
                severity = SignalSeverity.MEDIUM
                
            vel = behavioral.get("velocity_anomaly", 0.0)
            try:
                transaction_velocity = float(vel)
            except (ValueError, TypeError):
                transaction_velocity = 0.0
                
            signal = PrivacyPreservedSignal(
                signal_type=sig_type,
                severity=severity,
                confidence_score=float(pat.get("confidence", 0.0)),
                behavioral_fingerprint=behavioral,
                pattern_hash=pattern_hash,
                geographic_region="US",
                transaction_velocity=transaction_velocity,
                amount_percentile=0.95,
                originating_institution_id=self.institution_hash,
                target_institution_ids=[],
                regulatory_basis=pat.get("regulatory_basis", "BSA 5318(g)"),
                requires_sar=bool(pat.get("requires_sar", False))
            )
            signals.append(signal)
            
        if state_dict.get("signals_to_send") is None:
            state_dict["signals_to_send"] = []
        state_dict["signals_to_send"].extend(signals)
        
        return state_dict

    async def _node_process_received(self, state: Any) -> Dict[str, Any]:
        """
        Evaluate and decide action plans for incoming fraud signals.
        """
        state_dict = state if isinstance(state, dict) else state.model_dump()
        state_dict["status"] = AgentStatus.RECEIVING
        
        signals = state_dict.get("signals_received", [])
        if not signals:
            return state_dict
            
        if state_dict.get("actions_taken") is None:
            state_dict["actions_taken"] = []
            
        for sig in signals:
            if isinstance(sig, dict):
                sig_obj = PrivacyPreservedSignal(**sig)
            else:
                sig_obj = sig
                
            decision = None
            if self.llm is not None:
                system_prompt = "You are evaluating incoming fraud intelligence from a trusted partner institution on the Sanket network. Respond ONLY with JSON."
                
                sig_type_str = sig_obj.signal_type.value if hasattr(sig_obj.signal_type, "value") else str(sig_obj.signal_type)
                severity_str = sig_obj.severity.value if hasattr(sig_obj.severity, "value") else str(sig_obj.severity)
                
                human_prompt = f"""Partner institution detected {sig_type_str} with {sig_obj.confidence_score:.0%} confidence. 
Severity: {severity_str}.
Behavioral indicators: {json.dumps(sig_obj.behavioral_fingerprint)}

Respond with JSON:
{{
  "should_act": true,
  "action": "flag_account",
  "reasoning": "under 50 words explanation",
  "urgency": "immediate"
}}
Select action from: flag_account, freeze_transaction, escalate_to_human, request_verification, no_action.
Select urgency from: immediate, within_hour, monitor."""
                
                try:
                    messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=human_prompt)
                    ]
                    response = await self.llm.ainvoke(messages)
                    resp_text = response.content
                    
                    cleaned_text = resp_text.strip()
                    if cleaned_text.startswith("```json"):
                        cleaned_text = cleaned_text[7:]
                    elif cleaned_text.startswith("```"):
                        cleaned_text = cleaned_text[3:]
                    if cleaned_text.endswith("```"):
                        cleaned_text = cleaned_text[:-3]
                    cleaned_text = cleaned_text.strip()
                    
                    decision = json.loads(cleaned_text)
                except Exception as e:
                    self.logger.warning(f"Error analyzing incoming signal: {e}")
                    decision = None
                    
            if decision is None:
                # Fallback mock evaluation
                severity_enum = sig_obj.severity
                is_high_risk = severity_enum in [SignalSeverity.HIGH, SignalSeverity.CRITICAL] or str(severity_enum).upper() in ["HIGH", "CRITICAL"]
                if is_high_risk:
                    decision = {
                        "should_act": True,
                        "action": "flag_account",
                        "reasoning": "Mock: High severity signal from partner institution",
                        "urgency": "immediate"
                    }
                else:
                    decision = {
                        "should_act": False,
                        "action": "no_action",
                        "reasoning": "Mock: Low severity, monitoring",
                        "urgency": "monitor"
                    }
                    
            state_dict["actions_taken"].append({
                "signal_id": sig_obj.signal_id,
                "action": decision.get("action", "no_action"),
                "reasoning": decision.get("reasoning", ""),
                "urgency": decision.get("urgency", "monitor"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        return state_dict

    async def _node_execute_actions(self, state: Any) -> Dict[str, Any]:
        """
        Execute defensive measures and flag accounts locally.
        """
        state_dict = state if isinstance(state, dict) else state.model_dump()
        state_dict["status"] = AgentStatus.ACTING
        
        actions = state_dict.get("actions_taken", [])
        if state_dict.get("accounts_flagged") is None:
            state_dict["accounts_flagged"] = []
            
        for act in actions:
            action_type = act.get("action")
            if action_type == "flag_account":
                now_str = datetime.now(timezone.utc).isoformat()
                account_hash = hashlib.sha256(f"flagged_{now_str}".encode('utf-8')).hexdigest()[:8]
                state_dict["accounts_flagged"].append(account_hash)
                self.logger.info(f"Account flagged at {self.institution_name}")
            elif action_type == "freeze_transaction":
                self.logger.info(f"Transaction freeze requested at {self.institution_name}")
            elif action_type == "escalate_to_human":
                self.logger.info(f"ESCALATION: Human review required at {self.institution_name}")
                
        return state_dict

    async def _node_audit(self, state: Any) -> Dict[str, Any]:
        """
        Register session summary metrics and transition state to completed.
        """
        state_dict = state if isinstance(state, dict) else state.model_dump()
        state_dict["status"] = AgentStatus.COMPLETED
        state_dict["completed"] = True
        
        signals_to_send = state_dict.get("signals_to_send", [])
        signals_received = state_dict.get("signals_received", [])
        accounts_flagged = state_dict.get("accounts_flagged", [])
        actions_taken = state_dict.get("actions_taken", [])
        
        parts = [f"{self.institution_name} Agent Session:"]
        has_activity = False
        
        if signals_to_send:
            parts.append(f"Detected and prepared {len(signals_to_send)} fraud signal(s) for Sanket network.")
            has_activity = True
        if signals_received:
            parts.append(f"Received {len(signals_received)} intelligence signal(s) from partners.")
            has_activity = True
        if accounts_flagged:
            parts.append(f"Flagged {len(accounts_flagged)} account(s) for review.")
            has_activity = True
            
        if not has_activity:
            parts.append("No suspicious activity. Normal monitoring continued.")
            
        summary = " ".join(parts)
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "session_complete",
            "summary": summary,
            "signals_sent": len(signals_to_send),
            "signals_received": len(signals_received),
            "actions_taken": len(actions_taken),
            "accounts_flagged": len(accounts_flagged),
            "institution": self.institution_name
        }
        
        if state_dict.get("audit_trail") is None:
            state_dict["audit_trail"] = []
        state_dict["audit_trail"].append(audit_entry)
        state_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        return state_dict

    # --- Conditional Edge ---

    def _should_signal(self, state: Any) -> str:
        """
        Determines if there are detected fraud patterns that require signal transmission.
        """
        if isinstance(state, dict):
            detected = state.get("detected_patterns", [])
        else:
            detected = getattr(state, "detected_patterns", [])
        return "signal" if detected else "skip"

    # --- Public API ---

    async def run(
        self,
        transactions: List[Dict[str, Any]],
        received_signals: Optional[List[PrivacyPreservedSignal]] = None
    ) -> Dict[str, Any]:
        """
        Involves a single graph session processing local transactions and incoming signals.
        """
        initial_state = {
            "institution_id": self.institution_id,
            "institution_name": self.institution_name,
            "agent_id": f"agent_{self.institution_hash}",
            "session_id": str(uuid.uuid4()),
            "status": AgentStatus.IDLE,
            "raw_transactions": transactions,
            "detected_patterns": [],
            "signals_to_send": [],
            "signals_received": received_signals or [],
            "actions_taken": [],
            "accounts_flagged": [],
            "audit_trail": [],
            "arize_trace_id": None,
            "gemini_reasoning": None,
            "confidence_threshold": 0.85,
            "error": None,
            "completed": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = await self.graph.ainvoke(initial_state)
        
        if not isinstance(result, dict):
            return result.model_dump()
        return result
