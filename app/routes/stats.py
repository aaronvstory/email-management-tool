"""Statistics Blueprint - Phase 1B Route Modularization

Extracted from simple_app.py lines 1011, 2207, 2274, 2297
Routes: /api/stats, /api/unified-stats, /api/latency-stats, /stream/stats
"""
from flask import Blueprint, jsonify, Response, stream_with_context
from flask_login import login_required
import time
import json
from datetime import datetime
from app.utils.db import get_db, fetch_counts
from app.services.stats import get_stats

stats_bp = Blueprint('stats', __name__)

# TODO Phase 2: Unify stat sources (fetch_counts vs get_stats)

# Cache for unified stats (5s TTL)
_UNIFIED_CACHE = {'t': 0, 'v': None}


@stats_bp.route('/api/stats')
@login_required
def api_stats():
    """Get dashboard statistics"""
    data = get_stats()
    return jsonify(data)


@stats_bp.route('/api/unified-stats')
@login_required
def api_unified_stats():
    """Get unified statistics with released count"""
    now = time.time()
    if now - _UNIFIED_CACHE['t'] < 5 and _UNIFIED_CACHE['v'] is not None:
        return jsonify(_UNIFIED_CACHE['v'])

    counts = get_stats()
    conn = get_db()
    cur = conn.cursor()
    released = cur.execute("""
        SELECT COUNT(*) FROM email_messages
        WHERE interception_status='RELEASED' OR status IN ('SENT','APPROVED','DELIVERED')
    """).fetchone()[0]
    conn.close()

    val = {
        'total': counts['total'],
        'pending': counts['pending'],
        'held': counts['held'],
        'released': released
    }
    _UNIFIED_CACHE['t'] = now
    _UNIFIED_CACHE['v'] = val
    return jsonify(val)


@stats_bp.route('/api/latency-stats')
@login_required
def api_latency_stats():
    """Get latency statistics"""
    conn = get_db()
    cur = conn.cursor()
    avg_latency = cur.execute("""
        SELECT AVG(julianday(processed_at)-julianday(created_at))*86400000
        FROM email_messages
        WHERE processed_at IS NOT NULL
    """).fetchone()[0] or 0
    conn.close()
    return jsonify({'avg_processing_ms': round(avg_latency, 2)})


@stats_bp.route('/stream/stats')
@login_required
def stream_stats():
    """Server-sent events stream for real-time statistics"""
    def generate():
        while True:
            counts = get_stats()
            data = json.dumps({
                'pending': counts.get('pending', 0),
                'timestamp': datetime.utcnow().isoformat()
            })
            yield f"data: {data}\n\n"
            time.sleep(2)
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@stats_bp.route('/api/events')
@login_required
def api_events():
    """Legacy SSE endpoint for real-time updates (migrated from monolith)."""
    def generate():
        while True:
            counts = get_stats()
            pending = counts.get('pending', 0)
            payload = json.dumps({'pending': pending, 'timestamp': datetime.utcnow().isoformat()})
            yield f"data: {payload}\n\n"
            time.sleep(5)
    return Response(stream_with_context(generate()), mimetype='text/event-stream')
