import { useState, useEffect, useRef } from 'react';

export function useWebSocket(url) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [networkStats, setNetworkStats] = useState({
    institutions_connected: 0,
    signals_routed_total: 0
  });
  const ws = useRef(null);
  const reconnectTimer = useRef(null);

  useEffect(() => {
    const connect = () => {
      try {
        ws.current = new WebSocket(url);
        
        ws.current.onopen = () => {
          setConnected(true);
          console.log('Sanket WS connected');
        };
        
        ws.current.onclose = () => {
          setConnected(false);
          reconnectTimer.current = 
            setTimeout(connect, 3000);
        };
        
        ws.current.onerror = () => {
          setConnected(false);
        };
        
        ws.current.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data);
            
            if (msg.event === 'connected') {
              setNetworkStats(
                msg.network_stats || {});
            } else if (
              msg.type !== 'pong' && 
              msg.type !== 'heartbeat'
            ) {
              setEvents(prev => 
                [{ ...msg, _id: Date.now() }, 
                 ...prev].slice(0, 100)
              );
            }
          } catch(err) {
            console.error('WS parse error', err);
          }
        };
      } catch(err) {
        console.error('WS connect error', err);
      }
    };

    connect();

    const pingInterval = setInterval(() => {
      if (ws.current?.readyState === 1) {
        ws.current.send(
          JSON.stringify({ type: 'ping' }));
      }
    }, 25000);

    return () => {
      clearInterval(pingInterval);
      clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
  }, [url]);

  return { events, connected, networkStats };
}
