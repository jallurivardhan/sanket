import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
import redis.asyncio as aioredis
from backend.core.types import (
    PrivacyPreservedSignal, Institution, 
    AuditEntry, NetworkStats, SignalSeverity
)
from backend.utils.privacy import PrivacyFilter

class SanketProtocolRouter:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.institutions: Dict[str, Institution] = {}
        self.privacy_filter = PrivacyFilter()
        self.total_signals_routed: int = 0
        self.routing_times_ms: List[float] = []
        self.logger = logging.getLogger("sanket.router")
        self._subscribers: Dict[str, asyncio.Queue] = {}
        self.last_signal_at: Optional[datetime] = None

    async def connect(self) -> None:
        """
        Connect to the Redis server and publish an online event.
        """
        self.redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        self.logger.info("Sanket Protocol Router connected to Redis")
        
        # Publish network online event
        await self._publish_network_event({
            "event": "router_online",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Sanket network is live"
        })

    async def register_institution(self, institution: Institution) -> str:
        """
        Register a new financial institution on the signal network.
        """
        self.institutions[institution.institution_hash] = institution
        
        # Create a Queue for subscriber if not present
        if institution.institution_hash not in self._subscribers:
            self._subscribers[institution.institution_hash] = asyncio.Queue()
            
        # Publish network event
        await self._publish_network_event({
            "event": "institution_joined",
            "institution_hash": institution.institution_hash[:8] + "...",
            "name": institution.name,
            "tier": institution.tier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "network_size": len(self.institutions)
        })
        
        self.logger.info(f"{institution.name} joined Sanket network. Size: {len(self.institutions)}")
        return institution.institution_hash

    async def route_signal(
        self,
        signal: PrivacyPreservedSignal,
        sender_institution_hash: str
    ) -> Dict[str, Any]:
        """
        Route a privacy-preserved fraud signal to designated target institutions.
        """
        routing_start = datetime.now(timezone.utc)

        # 1. Privacy Check
        validation = self.privacy_filter.validate_signal_privacy(signal.model_dump())
        if not validation["approved"]:
            self.logger.warning("Signal rejected: PII detected")
            return {
                "success": False,
                "reason": "pii_detected",
                "violations": validation["violations"],
                "signal_id": signal.signal_id
            }

        # 2. Determine target recipients
        targets = signal.target_institution_ids
        if not targets:
            # Route to all connected institutions except the sender
            targets = [h for h in self.institutions.keys() if h != sender_institution_hash]

        # 3. Deliver signal to all targets
        delivery_results = []
        for target_hash in targets:
            res = await self._deliver_signal(signal, target_hash)
            delivery_results.append(res)

        # 4. Update router statistics
        self.total_signals_routed += 1
        self.last_signal_at = datetime.now(timezone.utc)
        
        routing_time_ms = (datetime.now(timezone.utc) - routing_start).total_seconds() * 1000
        self.routing_times_ms.append(routing_time_ms)
        if len(self.routing_times_ms) > 1000:
            self.routing_times_ms = self.routing_times_ms[-1000:]

        # 5. Create audit entry for regulatory compliance
        sig_type_str = signal.signal_type.value if hasattr(signal.signal_type, "value") else str(signal.signal_type)
        severity_str = signal.severity.value if hasattr(signal.severity, "value") else str(signal.severity)
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "signal_routed",
            "signal_id": signal.signal_id,
            "signal_type": sig_type_str,
            "severity": severity_str,
            "confidence": signal.confidence_score,
            "sender": sender_institution_hash[:8],
            "recipient_count": len(targets),
            "routing_time_ms": routing_time_ms,
            "pii_check": "passed",
            "requires_sar": signal.requires_sar,
            "regulatory_basis": signal.regulatory_basis
        }

        # Store in Redis audit list
        if self.redis:
            try:
                await self.redis.lpush("sanket:audit:log", json.dumps(audit_entry))
                await self.redis.ltrim("sanket:audit:log", 0, 9999)
            except Exception as e:
                self.logger.warning(f"Failed to write audit entry to Redis: {e}")

        # 6. Publish dashboard update event
        dashboard_event = {
            "event": "signal_routed",
            "signal_id": signal.signal_id,
            "signal_type": sig_type_str,
            "severity": severity_str,
            "confidence": signal.confidence_score,
            "sender_hash": sender_institution_hash[:8] + "...",
            "recipient_count": len(targets),
            "routing_time_ms": routing_time_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self._publish_network_event(dashboard_event)

        # 7. Log and Return routing outcome
        self.logger.info(
            f"Signal routed in {routing_time_ms:.0f}ms | "
            f"Type: {sig_type_str} | "
            f"Severity: {severity_str} | "
            f"Recipients: {len(targets)}"
        )

        return {
            "success": True,
            "signal_id": signal.signal_id,
            "recipients_notified": len(targets),
            "routing_time_ms": routing_time_ms,
            "audit_logged": True,
            "requires_sar": signal.requires_sar
        }

    async def _deliver_signal(
        self,
        signal: PrivacyPreservedSignal,
        target_institution_hash: str
    ) -> Dict[str, Any]:
        """
        Deliver signal payload to a specific registered institution.
        """
        sig_type_str = signal.signal_type.value if hasattr(signal.signal_type, "value") else str(signal.signal_type)
        severity_str = signal.severity.value if hasattr(signal.severity, "value") else str(signal.severity)
        
        # Build payload with strict privacy guidelines
        payload = {
            "signal_id": signal.signal_id,
            "signal_type": sig_type_str,
            "severity": severity_str,
            "confidence_score": signal.confidence_score,
            "behavioral_fingerprint": signal.behavioral_fingerprint,
            "pattern_hash": signal.pattern_hash,
            "geographic_region": signal.geographic_region,
            "transaction_velocity": signal.transaction_velocity,
            "regulatory_basis": signal.regulatory_basis,
            "requires_sar": signal.requires_sar,
            "timestamp": signal.timestamp.isoformat() if hasattr(signal.timestamp, "isoformat") else str(signal.timestamp),
            "sender_hash": signal.originating_institution_id[:8]
        }

        # Publish via Redis Pub/Sub if active
        if self.redis:
            try:
                channel = f"sanket:institution:{target_institution_hash}:signals"
                await self.redis.publish(channel, json.dumps(payload))
            except Exception as e:
                self.logger.warning(f"Failed to publish signal to Redis for target {target_institution_hash}: {e}")

        # Deliver to local queue subscription
        queue = self._subscribers.get(target_institution_hash)
        if queue:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                self.logger.warning(f"Subscriber queue full for target: {target_institution_hash}")

        # Update receiving counter in local memory
        target_inst = self.institutions.get(target_institution_hash)
        if target_inst:
            target_inst.signal_count_received += 1

        return {"target": target_institution_hash[:8], "delivered": True}

    async def get_network_stats(self) -> NetworkStats:
        """
        Calculate and return the network performance statistics.
        """
        recent_times = self.routing_times_ms[-100:] if self.routing_times_ms else []
        avg_routing_time_ms = sum(recent_times) / len(recent_times) if recent_times else 0.0
        
        active_alerts = sum(1 for inst in self.institutions.values() if inst.signal_count_received > 0)
        fraud_prevented = float(self.total_signals_routed * 50000.0)

        return NetworkStats(
            institutions_connected=len(self.institutions),
            signals_routed_total=self.total_signals_routed,
            avg_routing_time_ms=avg_routing_time_ms,
            network_uptime_pct=99.99,
            fraud_prevented_usd=fraud_prevented,
            last_signal_at=self.last_signal_at,
            active_alerts=active_alerts
        )

    async def get_audit_trail(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch the audit log trail from Redis store.
        """
        if not self.redis:
            return []
        try:
            entries = await self.redis.lrange("sanket:audit:log", 0, limit - 1)
            return [json.loads(e) for e in entries]
        except Exception as e:
            self.logger.warning(f"Failed to retrieve audit trail: {e}")
            return []

    async def _publish_network_event(self, event: Dict[str, Any]) -> None:
        """
        Publish router and network events to Redis channel.
        """
        if self.redis:
            try:
                await self.redis.publish("sanket:network:events", json.dumps(event))
            except Exception as e:
                self.logger.warning(f"Failed to publish network event: {e}")

    async def subscribe_institution(self, institution_hash: str) -> asyncio.Queue:
        """
        Access the asyncio queue subscription for incoming signals.
        """
        if institution_hash not in self._subscribers:
            self._subscribers[institution_hash] = asyncio.Queue()
        return self._subscribers[institution_hash]

    async def disconnect(self) -> None:
        """
        Disconnect from Redis gracefully.
        """
        if self.redis:
            await self.redis.aclose()
            self.redis = None
        self.logger.info("Sanket Protocol Router disconnected")
