import { useState, useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket';

const API = import.meta.env.VITE_API_URL 
  || 'http://localhost:8000';
const WS = import.meta.env.VITE_WS_URL 
  || 'ws://localhost:8000';

const SEVERITY_COLOR = {
  critical: '#EF4444',
  high: '#F97316', 
  medium: '#EAB308',
  low: '#22C55E'
};

const SIGNAL_LABELS = {
  fraud_pattern: 'Fraud Pattern',
  synthetic_identity: 'Synthetic Identity',
  account_takeover: 'Account Takeover',
  money_laundering: 'Money Laundering',
  coordinated_attack: 'Coordinated Attack'
};

function StatCard({ label, value, unit, color }) {
  return (
    <div style={{
      background: 'var(--bg3)',
      border: '1px solid var(--border)',
      borderRadius: 12,
      padding: '20px 24px',
      flex: 1
    }}>
      <div style={{ 
        fontSize: 11, 
        color: 'var(--text3)', 
        marginBottom: 8,
        letterSpacing: '0.5px'
      }}>
        {label.toUpperCase()}
      </div>
      <div style={{ 
        fontSize: 28, 
        fontWeight: 700,
        color: color || 'var(--text)',
        letterSpacing: '-1px'
      }}>
        {value}
        <span style={{ 
          fontSize: 13, 
          color: 'var(--text3)', 
          marginLeft: 4,
          fontWeight: 400
        }}>
          {unit}
        </span>
      </div>
    </div>
  );
}

function BankCard({ 
  name, role, color, active, 
  signalCount, txCount, label 
}) {
  return (
    <div style={{
      background: 'var(--bg3)',
      border: `1px solid ${active 
        ? color : 'var(--border)'}`,
      borderRadius: 14,
      padding: 24,
      width: 200,
      transition: 'border-color 0.4s',
      boxShadow: active 
        ? `0 0 20px ${color}22` : 'none'
    }}>
      <div style={{
        width: 36, height: 36,
        borderRadius: 8,
        background: `${color}22`,
        border: `1px solid ${color}44`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 18, marginBottom: 12
      }}>🏦</div>
      <div style={{ 
        fontSize: 13, fontWeight: 600,
        marginBottom: 4 
      }}>
        {name}
      </div>
      <div style={{
        fontSize: 10, color,
        background: `${color}22`,
        padding: '2px 8px',
        borderRadius: 4,
        display: 'inline-block',
        marginBottom: 16,
        letterSpacing: '0.5px'
      }}>
        {role}
      </div>
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: 6 
      }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between',
          fontSize: 11
        }}>
          <span style={{ color: 'var(--text3)' }}>
            {label}
          </span>
          <span style={{ 
            color, fontWeight: 600 
          }}>
            {signalCount}
          </span>
        </div>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between',
          fontSize: 11
        }}>
          <span style={{ color: 'var(--text3)' }}>
            Txns
          </span>
          <span style={{ 
            color: 'var(--text2)' 
          }}>
            {txCount}
          </span>
        </div>
      </div>
      {active && (
        <div style={{
          marginTop: 12,
          padding: '6px 10px',
          borderRadius: 6,
          background: `${color}15`,
          border: `1px solid ${color}44`,
          fontSize: 10, color,
          textAlign: 'center'
        }}>
          {role === 'ORIGINATOR' 
            ? '🚨 FRAUD DETECTED' 
            : '⚡ ALERT RECEIVED'}
        </div>
      )}
    </div>
  );
}

function EventCard({ event }) {
  const sev = event.severity;
  const color = sev 
    ? SEVERITY_COLOR[sev] : '#71717A';
  
  return (
    <div style={{
      padding: '10px 14px',
      borderRadius: 8,
      marginBottom: 6,
      background: sev 
        ? `${color}10` : 'var(--bg3)',
      border: `1px solid ${
        sev ? `${color}30` : 'var(--border)'}`,
      animation: 'fadeIn 0.3s ease'
    }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between',
        marginBottom: 3
      }}>
        <span style={{ 
          fontSize: 10, fontWeight: 600,
          color: color,
          letterSpacing: '0.5px'
        }}>
          {(event.event || event.type || 'EVENT')
            .toUpperCase().replace(/_/g, ' ')}
        </span>
        <span style={{ 
          fontSize: 10, 
          color: 'var(--text3)' 
        }}>
          {new Date(
            event.timestamp || Date.now()
          ).toLocaleTimeString()}
        </span>
      </div>
      {event.signal_type && (
        <div style={{ 
          fontSize: 11, 
          color: 'var(--text2)' 
        }}>
          {SIGNAL_LABELS[event.signal_type] 
            || event.signal_type}
          {event.confidence && (
            <span style={{ 
              color: 'var(--text3)', 
              marginLeft: 6 
            }}>
              {(event.confidence * 100).toFixed(0)}%
            </span>
          )}
        </div>
      )}
      {event.routing_time_ms > 0 && (
        <div style={{ 
          fontSize: 10, 
          color: '#22C55E', 
          marginTop: 3 
        }}>
          Routed in {
            Number(event.routing_time_ms)
              .toFixed(0)}ms
        </div>
      )}
      {event.banks_coordinated && (
        <div style={{ 
          fontSize: 10, 
          color: '#22C55E', 
          marginTop: 3 
        }}>
          {event.banks_coordinated} banks coordinated
        </div>
      )}
    </div>
  );
}

export default function App() {
  const { events, connected, networkStats } = 
    useWebSocket(`${WS}/ws/live`);
  const [running, setRunning] = useState(false);
  const [scenario, setScenario] = 
    useState('coordinated_fraud');
  const [result, setResult] = useState(null);
  const [animating, setAnimating] = useState(false);

  const runDemo = useCallback(async () => {
    setRunning(true);
    setResult(null);
    setAnimating(true);
    try {
      const res = await fetch(
        `${API}/api/v1/demo/run?scenario=${scenario}`,
        { method: 'POST' }
      );
      const data = await res.json();
      setResult(data);
    } catch(e) {
      console.error('Demo error:', e);
    } finally {
      setRunning(false);
      setTimeout(() => setAnimating(false), 2000);
    }
  }, [scenario]);

  const fraudCaught = result?.bank_a?.fraud_detected;
  const routingMs = result?.sanket?.routing_time_ms;

  return (
    <div style={{ 
      minHeight: '100vh',
      padding: '32px 24px',
      maxWidth: 1400,
      margin: '0 auto'
    }}>

      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 40
      }}>
        <div>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 12, 
            marginBottom: 6 
          }}>
            <div style={{
              width: 36, height: 36,
              borderRadius: 8,
              background: 
                'linear-gradient(135deg, #3B82F6, #8B5CF6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700, fontSize: 18
            }}>S</div>
            <span style={{ 
              fontSize: 26, fontWeight: 700,
              letterSpacing: '-0.5px'
            }}>Sanket</span>
            <span style={{
              fontSize: 11,
              padding: '3px 8px',
              borderRadius: 4,
              background: 'rgba(59,130,246,0.15)',
              color: '#3B82F6',
              border: '1px solid rgba(59,130,246,0.3)',
              letterSpacing: '0.5px'
            }}>BETA</span>
          </div>
          <p style={{ 
            fontSize: 13, 
            color: 'var(--text3)',
            letterSpacing: '0.3px'
          }}>
            The signal between financial minds
          </p>
        </div>

        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 8 
        }}>
          <div style={{
            width: 8, height: 8,
            borderRadius: '50%',
            background: connected 
              ? '#22C55E' : '#EF4444',
            boxShadow: connected 
              ? '0 0 8px #22C55E' : 'none'
          }}/>
          <span style={{ 
            fontSize: 12,
            color: connected 
              ? '#22C55E' : '#EF4444'
          }}>
            {connected 
              ? 'NETWORK LIVE' : 'CONNECTING...'}
          </span>
        </div>
      </div>

      {/* Stats Row */}
      <div style={{ 
        display: 'flex', 
        gap: 12, 
        marginBottom: 24 
      }}>
        <StatCard 
          label="Institutions" 
          value={networkStats
            .institutions_connected || 2}
          unit="connected"
        />
        <StatCard 
          label="Signals Routed"
          value={networkStats
            .signals_routed_total || 0}
          unit="total"
        />
        <StatCard 
          label="Fraud Prevented"
          value={`$${((networkStats
            .signals_routed_total || 0) * 50)
            .toLocaleString()}K`}
          unit="est."
          color="#22C55E"
        />
        <StatCard 
          label="Network Uptime"
          value="99.9"
          unit="%"
          color="#3B82F6"
        />
      </div>

      {/* Main Content */}
      <div style={{ 
        display: 'grid',
        gridTemplateColumns: '1fr 300px',
        gap: 16
      }}>

        {/* Left Panel */}
        <div>

          {/* Signal Flow */}
          <div style={{
            background: 'var(--bg3)',
            border: '1px solid var(--border)',
            borderRadius: 16,
            padding: 32,
            marginBottom: 16
          }}>
            <div style={{ 
              fontSize: 11,
              color: 'var(--text3)',
              marginBottom: 24,
              letterSpacing: '0.5px'
            }}>
              SIGNAL FLOW
            </div>

            <div style={{ 
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 16
            }}>
              <BankCard
                name="First National Bank"
                role="ORIGINATOR"
                color="#3B82F6"
                active={fraudCaught}
                signalCount={
                  result?.bank_a
                    ?.signals_generated || 0}
                txCount={
                  result?.bank_a
                    ?.transactions_analyzed || 0}
                label="Signals Sent"
              />

              {/* Signal Path */}
              <div style={{ 
                flex: 1, 
                textAlign: 'center',
                position: 'relative'
              }}>
                <div style={{
                  height: 2,
                  background: fraudCaught
                    ? 'linear-gradient(90deg, #3B82F6, #8B5CF6)'
                    : 'var(--border)',
                  borderRadius: 1,
                  transition: 'background 0.5s',
                  position: 'relative',
                  overflow: 'hidden'
                }}>
                  {animating && (
                    <div style={{
                      position: 'absolute',
                      top: -4,
                      width: 12, height: 12,
                      borderRadius: '50%',
                      background: '#3B82F6',
                      boxShadow: '0 0 12px #3B82F6',
                      animation: 'slide 1s ease forwards'
                    }}/>
                  )}
                </div>
                {routingMs > 0 && (
                  <div style={{
                    marginTop: 8,
                    fontSize: 11,
                    color: '#22C55E',
                    background: 'rgba(34,197,94,0.1)',
                    border: '1px solid rgba(34,197,94,0.3)',
                    padding: '2px 8px',
                    borderRadius: 4,
                    display: 'inline-block'
                  }}>
                    {Number(routingMs).toFixed(0)}ms
                  </div>
                )}
                <div style={{ 
                  fontSize: 11,
                  color: 'var(--text3)',
                  marginTop: 6
                }}>
                  via Sanket
                </div>
              </div>

              <BankCard
                name="Metro Financial"
                role="RECIPIENT"
                color="#8B5CF6"
                active={
                  result?.bank_b
                    ?.signals_received > 0}
                signalCount={
                  result?.bank_b
                    ?.signals_received || 0}
                txCount={
                  result?.bank_b
                    ?.accounts_flagged || 0}
                label="Signals Received"
              />
            </div>

            {/* Result Banner */}
            {result && (
              <div style={{
                marginTop: 24,
                padding: '14px 20px',
                borderRadius: 10,
                background: fraudCaught
                  ? 'rgba(34,197,94,0.08)'
                  : 'var(--bg2)',
                border: `1px solid ${fraudCaught 
                  ? 'rgba(34,197,94,0.25)' 
                  : 'var(--border)'}`,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <div style={{ 
                    fontSize: 13, fontWeight: 600,
                    color: fraudCaught 
                      ? '#22C55E' : 'var(--text3)'
                  }}>
                    {fraudCaught 
                      ? '✓ FRAUD DETECTED & NETWORK ALERTED'
                      : '✓ NO SUSPICIOUS ACTIVITY DETECTED'}
                  </div>
                  {fraudCaught && (
                    <div style={{ 
                      fontSize: 11,
                      color: 'var(--text3)',
                      marginTop: 4
                    }}>
                      Zero raw data shared · 
                      Full audit logged · 
                      BSA compliant
                    </div>
                  )}
                </div>
                {fraudCaught && routingMs > 0 && (
                  <div style={{ 
                    fontSize: 22,
                    fontWeight: 700,
                    color: '#22C55E',
                    letterSpacing: '-0.5px'
                  }}>
                    {Number(routingMs).toFixed(0)}ms
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Controls */}
          <div style={{
            background: 'var(--bg3)',
            border: '1px solid var(--border)',
            borderRadius: 16,
            padding: 24,
            display: 'flex',
            alignItems: 'flex-end',
            gap: 16
          }}>
            <div style={{ flex: 1 }}>
              <div style={{ 
                fontSize: 11,
                color: 'var(--text3)',
                marginBottom: 8,
                letterSpacing: '0.5px'
              }}>
                SCENARIO
              </div>
              <select
                value={scenario}
                onChange={e => 
                  setScenario(e.target.value)}
                style={{
                  width: '100%',
                  background: 'var(--bg2)',
                  border: '1px solid var(--border2)',
                  borderRadius: 8,
                  padding: '10px 14px',
                  color: 'var(--text)',
                  fontSize: 13,
                  fontFamily: 'var(--font)',
                  cursor: 'pointer'
                }}
              >
                <option value="coordinated_fraud">
                  Coordinated Multi-Bank Fraud
                </option>
                <option value="synthetic_identity">
                  Synthetic Identity Attack
                </option>
                <option value="normal">
                  Normal Baseline
                </option>
              </select>
            </div>

            <button
              onClick={runDemo}
              disabled={running}
              style={{
                padding: '11px 32px',
                borderRadius: 10,
                background: running 
                  ? 'var(--bg2)'
                  : 'linear-gradient(135deg, #3B82F6, #8B5CF6)',
                border: 'none',
                color: 'var(--text)',
                fontSize: 13, fontWeight: 600,
                cursor: running 
                  ? 'not-allowed' : 'pointer',
                opacity: running ? 0.5 : 1,
                letterSpacing: '0.3px',
                whiteSpace: 'nowrap',
                transition: 'opacity 0.2s'
              }}
            >
              {running ? 'RUNNING...' : 'RUN DEMO'}
            </button>
          </div>

          {/* Gemini Reasoning */}
          {result?.bank_a?.reasoning && (
            <div style={{
              marginTop: 16,
              background: 'var(--bg3)',
              border: '1px solid var(--border)',
              borderRadius: 16,
              padding: 24
            }}>
              <div style={{ 
                fontSize: 11,
                color: 'var(--text3)',
                marginBottom: 12,
                letterSpacing: '0.5px'
              }}>
                GEMINI REASONING
              </div>
              <p style={{ 
                fontSize: 13,
                color: 'var(--text2)',
                lineHeight: 1.7
              }}>
                {result.bank_a.reasoning}
              </p>
            </div>
          )}
        </div>

        {/* Right Panel — Live Feed */}
        <div style={{
          background: 'var(--bg3)',
          border: '1px solid var(--border)',
          borderRadius: 16,
          padding: 20,
          maxHeight: 600,
          overflowY: 'auto'
        }}>
          <div style={{ 
            fontSize: 11,
            color: 'var(--text3)',
            marginBottom: 16,
            letterSpacing: '0.5px'
          }}>
            LIVE SIGNAL FEED
          </div>
          {events.length === 0 ? (
            <div style={{ 
              color: 'var(--text3)',
              fontSize: 12,
              textAlign: 'center',
              marginTop: 40
            }}>
              Waiting for signals...
            </div>
          ) : (
            events.map(ev => (
              <EventCard key={ev._id} event={ev} />
            ))
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{
        marginTop: 32,
        paddingTop: 20,
        borderTop: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: 11,
        color: 'var(--text3)'
      }}>
        <span>
          Built with Gemini 3.1 · 
          Google Cloud Agent Builder · 
          Arize Phoenix
        </span>
        <span>
          Google Cloud Rapid Agent Hackathon 2026
        </span>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slide {
          from { left: 0; opacity: 1; }
          to { left: 100%; opacity: 0; }
        }
        select option { background: #18181B; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { 
          background: transparent; }
        ::-webkit-scrollbar-thumb { 
          background: rgba(255,255,255,0.1);
          border-radius: 2px; }
      `}</style>
    </div>
  );
}
