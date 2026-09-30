from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def get_schedule_type(schedule):
    """Determine schedule type category: 'crontab', 'interval', 'solar', or 'custom'."""
    if schedule is None:
        return 'custom'
    if isinstance(schedule, (int, float, timedelta)):
        return 'interval'
    sched_type = type(schedule).__name__.lower()
    if 'crontab' in sched_type:
        return 'crontab'
    if 'solar' in sched_type or (hasattr(schedule, 'event') and hasattr(schedule, 'lat')):
        return 'solar'
    if 'schedule' in sched_type or hasattr(schedule, 'run_every'):
        return 'interval'
    return 'custom'


def format_schedule(schedule):
    """Format a Celery schedule object, timedelta, solar, or primitive into a readable string."""
    if schedule is None:
        return ""
    if isinstance(schedule, (int, float)):
        return f"every {schedule:g}s"
    if isinstance(schedule, timedelta):
        total_seconds = schedule.total_seconds()
        if total_seconds < 60:
            return f"every {total_seconds:g}s"
        minutes, secs = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        parts = []
        if days:
            parts.append(f"{int(days)}d")
        if hours:
            parts.append(f"{int(hours)}h")
        if minutes:
            parts.append(f"{int(minutes)}m")
        if secs:
            parts.append(f"{int(secs)}s")
        return f"every {' '.join(parts)}"

    # Check for solar schedule
    if hasattr(schedule, 'event') and hasattr(schedule, 'lat') and hasattr(schedule, 'lon'):
        return f"solar: {schedule.event} ({schedule.lat}, {schedule.lon})"

    return str(schedule)


def get_latest_task_executions(events, target_names=None):
    """Return a mapping of task_name -> latest task dict from events state.

    If target_names is specified, only tasks with matching names will be processed.
    """
    if not events or not hasattr(events, 'state') or not hasattr(events.state, 'tasks'):
        return {}

    latest_by_name = {}
    task_map = getattr(events.state.tasks, 'data', events.state.tasks)
    target_set = set(target_names) if target_names else None

    if isinstance(task_map, dict):
        for task in task_map.values():
            name = getattr(task, 'name', None)
            if not name or (target_set and name not in target_set):
                continue
            ts = getattr(task, 'received', None) or getattr(task, 'timestamp', None) or 0
            existing = latest_by_name.get(name)
            if existing is None:
                latest_by_name[name] = task
            else:
                existing_ts = getattr(existing, 'received', None) or getattr(existing, 'timestamp', None) or 0
                if ts >= existing_ts:
                    latest_by_name[name] = task
        return latest_by_name

    # Fallback to tasks_by_type if tasks is not a dictionary
    if target_names and hasattr(events.state, 'tasks_by_type') and callable(events.state.tasks_by_type):
        try:
            for name in target_names:
                tasks_list = events.state.tasks_by_type(name)
                for task in tasks_list:
                    ts = getattr(task, 'received', None) or getattr(task, 'timestamp', None) or 0
                    existing = latest_by_name.get(name)
                    if existing is None:
                        latest_by_name[name] = task
                    else:
                        existing_ts = getattr(existing, 'received', None) or getattr(existing, 'timestamp', None) or 0
                        if ts >= existing_ts:
                            latest_by_name[name] = task
        except TypeError:
            pass

    return latest_by_name


def get_recurring_tasks(capp, events=None):
    """Extract and parse registered Celery Beat recurring tasks from celery configuration."""
    beat_schedule = {}
    if hasattr(capp, 'conf'):
        beat_schedule = capp.conf.beat_schedule or capp.conf.get('BEAT_SCHEDULE') or {}

    if not isinstance(beat_schedule, dict):
        return []

    # Collect target task names for fast indexed lookup
    target_task_names = {
        (entry.get('task') if isinstance(entry, dict) else getattr(entry, 'task', None))
        for entry in beat_schedule.values()
    }
    target_task_names.discard(None)

    latest_tasks = get_latest_task_executions(events, target_names=target_task_names) if events else {}
    results = []

    for name, entry in beat_schedule.items():
        if isinstance(entry, dict):
            task_name = entry.get('task')
            schedule_val = entry.get('schedule')
            args = entry.get('args', ())
            kwargs = entry.get('kwargs', {})
            options = entry.get('options', {})
            relative = entry.get('relative', False)
            total_run_count = entry.get('total_run_count')
            last_run_at = entry.get('last_run_at')
        else:
            task_name = getattr(entry, 'task', None)
            schedule_val = getattr(entry, 'schedule', None)
            args = getattr(entry, 'args', ())
            kwargs = getattr(entry, 'kwargs', {})
            options = getattr(entry, 'options', {})
            relative = getattr(entry, 'relative', False)
            total_run_count = getattr(entry, 'total_run_count', None)
            last_run_at = getattr(entry, 'last_run_at', None)

        last_exec_info = None
        if task_name and task_name in latest_tasks:
            t = latest_tasks[task_name]
            last_exec_info = {
                'uuid': getattr(t, 'uuid', None),
                'state': getattr(t, 'state', None),
                'received': getattr(t, 'received', None) or getattr(t, 'timestamp', None),
                'started': getattr(t, 'started', None),
                'succeeded': getattr(t, 'succeeded', None),
                'failed': getattr(t, 'failed', None),
                'runtime': getattr(t, 'runtime', None),
                'result': getattr(t, 'result', None) or getattr(t, 'exception', None),
            }

        results.append({
            'name': str(name),
            'task': str(task_name) if task_name else '',
            'type': get_schedule_type(schedule_val),
            'schedule': format_schedule(schedule_val),
            'schedule_raw': str(schedule_val) if schedule_val is not None else '',
            'args': list(args) if isinstance(args, (list, tuple)) else args,
            'kwargs': dict(kwargs) if isinstance(kwargs, dict) else kwargs,
            'options': dict(options) if isinstance(options, dict) else options,
            'relative': bool(relative),
            'total_run_count': total_run_count,
            'last_run_at': str(last_run_at) if last_run_at is not None else None,
            'last_execution': last_exec_info,
        })

    results.sort(key=lambda s: s['name'].lower())
    return results

