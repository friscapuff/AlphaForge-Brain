from src.services.events import event_stream


def test_event_ordering_and_heartbeat_interval(freeze_time):
    phases = ["start", "middle", "end"]
    events = list(event_stream(phases, heartbeat_interval_sec=10))
    assert events[0]["type"] == "heartbeat"
    # Timestamp should match frozen time (date/time prefix)
    assert events[0]["ts"].startswith(freeze_time.now().isoformat()[:19])
    assert events[0]["interval"] == 10
    # Phases in order
    phase_events = [e for e in events if e["type"] == "phase"]
    assert [e["phase"] for e in phase_events] == phases
    # Terminal last
    assert events[-1]["type"] == "terminal"
    # Exactly len(phases)+2 events
    assert len(events) == len(phases) + 2
