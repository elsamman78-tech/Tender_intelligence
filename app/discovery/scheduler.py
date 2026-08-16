from threading import Thread, Event, Lock
from time import monotonic
from .orchestrator import run_known_sources, run_open_discovery, validate_candidates, profile_candidates, bootstrap
from .source_health import audit_all_sources
from ..agents.loop import run_discovery_supervisor
from ..db import SessionLocal
from ..config import (
    DISCOVERY_ENABLED, DISCOVERY_SCAN_INTERVAL_MINUTES, OPEN_DISCOVERY_INTERVAL_MINUTES,
    SOURCE_HEALTH_AUDIT_INTERVAL_MINUTES, SOURCE_HEALTH_AUDIT_BATCH,
    AUTONOMOUS_AGENTS_ENABLED, AUTONOMOUS_AGENT_INTERVAL_MINUTES,
)

_thread=None
_stop=Event()
_lock=Lock()


def _with_db(fn,*args,**kwargs):
    db=SessionLocal()
    try: return fn(db,*args,**kwargs)
    finally: db.close()


def _loop():
    _with_db(bootstrap)
    now0=monotonic()
    # Small offsets prevent all network-heavy jobs from starting at the same second after launch.
    last_known=now0-DISCOVERY_SCAN_INTERVAL_MINUTES*60+60
    last_open=now0-OPEN_DISCOVERY_INTERVAL_MINUTES*60+120
    last_profile=now0-max(60,OPEN_DISCOVERY_INTERVAL_MINUTES//2)*60+180
    last_validate=now0-max(30,DISCOVERY_SCAN_INTERVAL_MINUTES//2)*60+240
    last_health=now0-SOURCE_HEALTH_AUDIT_INTERVAL_MINUTES*60+300
    last_agent=now0-AUTONOMOUS_AGENT_INTERVAL_MINUTES*60+600
    while not _stop.is_set():
        now=monotonic()
        try:
            if now-last_known >= DISCOVERY_SCAN_INTERVAL_MINUTES*60:
                _with_db(run_known_sources); last_known=now
            if now-last_open >= OPEN_DISCOVERY_INTERVAL_MINUTES*60:
                _with_db(run_open_discovery); last_open=now
            if now-last_profile >= max(60,OPEN_DISCOVERY_INTERVAL_MINUTES//2)*60:
                _with_db(profile_candidates,20); last_profile=now
            if now-last_validate >= max(30,DISCOVERY_SCAN_INTERVAL_MINUTES//2)*60:
                _with_db(validate_candidates,50); last_validate=now
            if now-last_health >= SOURCE_HEALTH_AUDIT_INTERVAL_MINUTES*60:
                _with_db(audit_all_sources,SOURCE_HEALTH_AUDIT_BATCH); last_health=now
            if AUTONOMOUS_AGENTS_ENABLED and now-last_agent >= AUTONOMOUS_AGENT_INTERVAL_MINUTES*60:
                _with_db(run_discovery_supervisor,
                         'Autonomously improve worldwide source coverage, find engineering consultancy opportunities, verify candidates, and measure gaps.',
                         1)
                last_agent=now
        except Exception:
            # Individual jobs persist their own failure/health status; the loop must survive.
            pass
        _stop.wait(30)


def start_scheduler():
    global _thread
    if not DISCOVERY_ENABLED: return None
    with _lock:
        if _thread and _thread.is_alive(): return _thread
        _stop.clear(); _thread=Thread(target=_loop,name='tender-discovery-scheduler',daemon=True); _thread.start(); return _thread


def stop_scheduler():
    global _thread
    _stop.set()
    if _thread and _thread.is_alive(): _thread.join(timeout=2)
    _thread=None
