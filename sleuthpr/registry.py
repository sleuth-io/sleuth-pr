import logging
from importlib import import_module
from typing import List

from django.apps import apps

from sleuthpr.models import ActionType
from sleuthpr.models import ConditionVariableType
from sleuthpr.models import TriggerType


logger = logging.getLogger(__name__)


def _modules(field_name: str):
    for name, app in apps.app_configs.items():
        try:
            module = import_module(f"{app.name}.sleuthpr")
            if hasattr(module, field_name):
                yield name, getattr(module, field_name)
        except ModuleNotFoundError:
            pass


_condition_variable_types = {}
_trigger_types = {}
_action_types = {}


def _init():
    if _condition_variable_types:
        return

    for name, values in _modules("condition_variable_types"):
        logger.info(f"Loading condition_variable_types from {name}")
        for value in values:
            _condition_variable_types[value.key] = value

    for name, values in _modules("trigger_types"):
        logger.info(f"Loading trigger_type from {name}")
        for value in values:
            _trigger_types[value.key] = value

    for name, values in _modules("action_types"):
        logger.info(f"Loading action_types from {name}")
        for value in values:
            _action_types[value.key] = value


def get_all_condition_variable_types() -> List[ConditionVariableType]:
    _init()
    return list(_condition_variable_types.values())


def get_all_trigger_types() -> List[TriggerType]:
    _init()
    return list(_trigger_types.values())


def get_all_action_types() -> List[ActionType]:
    _init()
    return list(_action_types.values())


def get_condition_variable_type(key: str) -> ConditionVariableType:
    _init()
    result = _condition_variable_types.get(key)
    if not result:
        raise ValueError(f"Unknown condition variable type {key}")
    return result


def get_trigger_type(key: str) -> TriggerType:
    _init()
    result = _trigger_types.get(key)
    if not result:
        raise ValueError(f"Unknown trigger type {key}")
    return result


def get_action_type(key: str) -> ActionType:
    _init()
    result = _action_types.get(key)
    if not result:
        raise ValueError(f"Unknown action type {key}")
    return result
