import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from sleuthpr.services.github.tasks import event_task

logger = logging.getLogger(__name__)


@csrf_exempt
def on_event(request):
    event_name = request.headers.get("X-GitHub-Event")
    # delivery_id = request.headers.get("X-GitHub-Delivery")

    # todo: validate signature

    body = request.body.decode()
    data = json.loads(body)
    logger.debug(f"event: {event_name}")

    event_task.delay(event_name, data)

    return HttpResponse(f"Event received! - {body}", status=202)
