from celery.events.state import Task


def iter_tasks(app, limit=None, type=None, worker=None, state=None):
    i = 0
    events_state = app.events.state
    for uuid, task in events_state.tasks_by_timestamp():
        if type and task.name != type:
            continue
        if worker and task.worker and task.worker.hostname != worker:
            continue
        if state and task.state != state:
            continue
        yield uuid, task
        i += 1
        if i == limit:
            break


def get_task_by_id(app, task_id):
    if hasattr(Task, '_fields'):  # Old version
        return app.events.state.tasks.get(task_id)
    else:
        _fields = Task._defaults.keys()
        task = app.events.state.tasks.get(task_id)
        if task is not None:
            task._fields = _fields
        return task
