import logging

from django.http import HttpResponse
from django.http import JsonResponse

from sleuthpr import registry

# Create your views here.

logger = logging.getLogger(__name__)


def index(request):
    return HttpResponse(f"Hello, world. You're at the sleuthpr app.")


def welcome(request):
    return HttpResponse(f"Welcome new user!")


def api(request):
    return JsonResponse(
        data=dict(
            variables={
                item.key: dict(
                    label=item.label, type=str(item.type), triggers=[trig.key for trig in item.default_triggers]
                )
                for item in registry.get_all_condition_variable_types()
            },
            triggers={item.key: dict(label=item.label) for item in registry.get_all_trigger_types()},
            actions={item.key: dict(label=item.label) for item in registry.get_all_action_types()},
        )
    )
