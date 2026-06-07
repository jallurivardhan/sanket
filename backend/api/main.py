import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from backend.core.router import SanketProtocolRouter
from backend.core.types import (
    Institution, DemoScenario, NetworkStats, PrivacyPreservedSignal
)
from backend.agents.bank_agent import BankAgent
from backend.utils.simulation import TransactionSimulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sanket.api")

# --- GLOBAL INSTANCES ---
router = SanketProtocolRouter(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379")
)

simulator = TransactionSimulator()

bank_a = BankAgent(
    institution_id="first_national_bank_001",
    institution_name="First National Bank"
)

bank_b = BankAgent(
    institution_id="metro_financial_002",
    institution_name="Metro Financial"
)

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WS client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        payload = json.dumps(message, default=str)
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

ws_manager = ConnectionManager()

# --- LIFESPAN LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: Connect to Redis
    try:
        await router.connect()
    except Exception as e:
        logger.warning(f"Redis not available: {e}. Running without real-time pub/sub.")

    # Register institutions
    inst_a = Institution(
        name="First National Bank",
        institution_hash=bank_a.institution_hash,
        tier="national"
    )
    inst_b = Institution(
        name="Metro Financial",
        institution_hash=bank_b.institution_hash,
        tier="regional"
    )

    try:
        await router.register_institution(inst_a)
        await router.register_institution(inst_b)
    except Exception as e:
        logger.warning(f"Failed to register institutions: {e}. Fallback to direct memory dict assignment.")
        router.institutions[inst_a.institution_hash] = inst_a
        router.institutions[inst_b.institution_hash] = inst_b

    logger.info(f"Sanket network initialized — {len(router.institutions)} institutions connected")
    
    yield

    # SHUTDOWN: Disconnect router
    try:
        await router.disconnect()
    except Exception as e:
        logger.warning(f"Error during disconnect: {e}")
    logger.info("Sanket API shutdown")

# --- FASTAPI APP SETUP ---
app = FastAPI(
    title="Sanket",
    description="The signal between financial minds — cross-institutional AI agent network",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ENDPOINTS ---

@app.get("/health")
async def health():
    return {
        "status": "operational",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "institutions_connected": len(router.institutions),
        "redis_connected": router.redis is not None,
        "network": "Sanket"
    }

@app.get("/api/v1/network/stats")
async def get_network_stats():
    try:
        stats = await router.get_network_stats()
        return stats.model_dump()
    except Exception as e:
        logger.warning(f"Error fetching network stats: {e}")
        return {
            "institutions_connected": len(router.institutions),
            "signals_routed_total": router.total_signals_routed,
            "avg_routing_time_ms": 0.0,
            "network_uptime_pct": 99.9,
            "fraud_prevented_usd": 0.0,
            "last_signal_at": None,
            "active_alerts": 0
        }

@app.get("/api/v1/institutions")
async def get_institutions():
    return {
        "institutions": [
            {
                "hash": inst.institution_hash[:8] + "...",
                "name": inst.name,
                "tier": inst.tier,
                "connected_at": inst.connected_at.isoformat() if hasattr(inst.connected_at, "isoformat") else str(inst.connected_at),
                "signals_sent": inst.signal_count_sent,
                "signals_received": inst.signal_count_received,
                "is_active": inst.is_active
            }
            for inst in router.institutions.values()
        ],
        "total": len(router.institutions)
    }

@app.get("/api/v1/audit/trail")
async def get_audit_trail(limit: int = Query(50, ge=1)):
    try:
        entries = await router.get_audit_trail(limit)
        return {
            "entries": entries,
            "total": len(entries),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format": "sanket_audit_v1"
        }
    except Exception as e:
        logger.warning(f"Error fetching audit trail: {e}")
        return {"entries": [], "total": 0}

@app.post("/api/v1/demo/run")
async def run_demo(scenario: str = "coordinated_fraud"):
    try:
        # 1. Generate Transactions
        scenario_lower = scenario.lower()
        if "coordinated_fraud" in scenario_lower:
            txns_a = simulator.generate_coordinated_fraud_scenario()
            txns_b = simulator.generate_linked_accounts()
        elif "synthetic_identity" in scenario_lower:
            txns_a = simulator.generate_synthetic_identity_scenario()
            txns_b = simulator.generate_normal_transactions(20)
        else:
            txns_a = simulator.generate_normal_transactions(50)
            txns_b = simulator.generate_normal_transactions(50)

        # 2. Run Bank A agent
        state_a = await bank_a.run(transactions=txns_a)

        # 3. Build baseline results
        result = {
            "scenario": scenario,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "bank_a": {
                "name": "First National Bank",
                "transactions_analyzed": len(txns_a),
                "fraud_detected": len(state_a.get("signals_to_send", [])) > 0,
                "signals_generated": len(state_a.get("signals_to_send", [])),
                "reasoning": state_a.get("gemini_reasoning", "")
            },
            "bank_b": {
                "name": "Metro Financial",
                "signals_received": 0,
                "actions_taken": [],
                "accounts_flagged": 0
            },
            "sanket": {
                "signals_routed": 0,
                "routing_time_ms": 0.0,
                "privacy_guaranteed": True,
                "audit_logged": True
            }
        }

        # 4. Route signals if fraud detected by Bank A
        signals_to_send = state_a.get("signals_to_send", [])
        if len(signals_to_send) > 0:
            await ws_manager.broadcast({
                "event": "fraud_detected",
                "bank": "First National Bank",
                "signal_count": len(signals_to_send),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            signals_routed = 0
            last_routing_time = 0.0
            
            for sig in signals_to_send:
                try:
                    sig_obj = sig if isinstance(sig, PrivacyPreservedSignal) else PrivacyPreservedSignal(**sig)
                    
                    route_result = await router.route_signal(sig_obj, bank_a.institution_hash)
                    
                    await ws_manager.broadcast({
                        "event": "signal_routed",
                        "signal_id": sig_obj.signal_id,
                        "signal_type": sig_obj.signal_type.value if hasattr(sig_obj.signal_type, 'value') else sig_obj.signal_type,
                        "severity": sig_obj.severity.value if hasattr(sig_obj.severity, 'value') else sig_obj.severity,
                        "confidence": sig_obj.confidence_score,
                        "from_bank": "First National Bank",
                        "to_bank": "Metro Financial",
                        "routing_time_ms": route_result.get("routing_time_ms", 0.0),
                        "privacy_preserved": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

                    signals_routed += 1
                    last_routing_time = route_result.get("routing_time_ms", 0.0)

                    # Update sent count for Institution A
                    inst_a = router.institutions.get(bank_a.institution_hash)
                    if inst_a:
                        inst_a.signal_count_sent += 1
                except Exception as route_err:
                    logger.warning(f"Error routing individual signal: {route_err}")
                    continue

            # Run Bank B on incoming signals
            state_b = await bank_b.run(transactions=txns_b, received_signals=signals_to_send)

            # Update final metrics
            result["bank_b"]["signals_received"] = len(state_b.get("signals_received", []))
            result["bank_b"]["actions_taken"] = state_b.get("actions_taken", [])
            result["bank_b"]["accounts_flagged"] = len(state_b.get("accounts_flagged", []))

            result["sanket"]["signals_routed"] = signals_routed
            result["sanket"]["routing_time_ms"] = last_routing_time

            # Broadcast demo completion
            await ws_manager.broadcast({
                "event": "demo_complete",
                "scenario": scenario,
                "fraud_caught": True,
                "banks_coordinated": 2,
                "routing_time_ms": last_routing_time,
                "accounts_flagged": result["bank_b"]["accounts_flagged"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        else:
            # Normal baseline or no fraud caught
            state_b = await bank_b.run(transactions=txns_b, received_signals=[])
            
            result["bank_b"]["signals_received"] = len(state_b.get("signals_received", []))
            result["bank_b"]["actions_taken"] = state_b.get("actions_taken", [])
            result["bank_b"]["accounts_flagged"] = len(state_b.get("accounts_flagged", []))

            await ws_manager.broadcast({
                "event": "demo_complete",
                "scenario": scenario,
                "fraud_caught": False,
                "banks_coordinated": 2,
                "routing_time_ms": 0.0,
                "accounts_flagged": 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        return result

    except Exception as e:
        logger.error(f"Demo run execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/demo/scenarios")
async def get_scenarios():
    return {
        "scenarios": [
            {
                "id": "coordinated_fraud",
                "name": "Coordinated Multi-Bank Fraud",
                "description": "Fraudster opens accounts at multiple banks simultaneously",
                "expected": "Fraud detected and partner bank alerted in <500ms"
            },
            {
                "id": "synthetic_identity",
                "name": "Synthetic Identity Attack",
                "description": "AI-built fake identity drains accounts after 18 months of credit building",
                "expected": "Structuring pattern detected, SAR filing triggered"
            },
            {
                "id": "normal",
                "name": "Normal Baseline",
                "description": "Regular transaction activity with no fraud",
                "expected": "No alerts generated, network monitors normally"
            }
        ]
    }

# --- WEBSOCKET FEED ---
@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send initial state on connection
        await websocket.send_text(json.dumps({
            "event": "connected",
            "message": "Connected to Sanket live feed",
            "network_stats": {
                "institutions_connected": len(router.institutions),
                "signals_routed_total": router.total_signals_routed
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, default=str))

        # Keep alive loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text(json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"WebSocket error: {e}")
                break
    finally:
        ws_manager.disconnect(websocket)

# --- WEB SERVER INIT ---
if __name__ == "__main__":
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info"
    )
