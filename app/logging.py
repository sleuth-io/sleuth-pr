from logging import Filter
from logging import LogRecord

from opentracing import tracer


class SpanLoggerFilter(Filter):
    def filter(self, record: LogRecord) -> int:
        scope = tracer.scope_manager.active
        if scope:
            event_name = scope.span.tags.get("event_name", "")
            task_id = scope.span.tags.get("celery.task_id", "")[-6:]
            if event_name:
                record.event_id = f"[{task_id}:{event_name}]"
            elif task_id:
                record.event_id = f"[{task_id}]"
            else:
                record.event_id = ""
        else:
            record.event_id = ""
        return True
