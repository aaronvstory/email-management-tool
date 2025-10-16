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
from app.extensions import csrf
from app.services.stats import get_stats
import statistics

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
        WHERE (interception_status='RELEASED' OR status IN ('APPROVED','DELIVERED'))
          AND (direction IS NULL OR direction!='outbound')
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


_LAT_CACHE = {'t': 0.0, 'v': None}


def _percentile(sorted_vals, pct: float) -> float:
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    pos = (n - 1) * pct
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return float(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac)


@stats_bp.route('/api/latency-stats')
def api_latency_stats():
    """Get latency statistics with 10s cache"""
    now = time.time()
    if _LAT_CACHE['v'] is not None and (now - _LAT_CACHE['t']) < 10:
        return jsonify(_LAT_CACHE['v'])

    conn = get_db(); cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT latency_ms FROM email_messages
        WHERE latency_ms IS NOT NULL
        ORDER BY id DESC LIMIT 1000
        """
    ).fetchall()
    conn.close()

    vals = [float(r[0]) for r in rows if r[0] is not None]
    vals.sort()
    count = len(vals)
    if count == 0:
        payload = {
            'count': 0,
            'min': 0, 'p50': 0, 'p90': 0, 'p95': 0, 'p99': 0, 'max': 0,
            'mean': 0, 'median': 0
        }
    else:
        payload = {
            'count': count,
            'min': float(vals[0]),
            'p50': _percentile(vals, 0.50),
            'p90': _percentile(vals, 0.90),
            'p95': _percentile(vals, 0.95),
            'p99': _percentile(vals, 0.99),
            'max': float(vals[-1]),
            'mean': float(statistics.fmean(vals) if hasattr(statistics, 'fmean') else sum(vals)/count),
            'median': float(statistics.median(vals)),
        }

    _LAT_CACHE['t'] = now
    _LAT_CACHE['v'] = payload
    return jsonify(payload)


@stats_bp.route('/stream/stats')
@csrf.exempt
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
@csrf.exempt
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
