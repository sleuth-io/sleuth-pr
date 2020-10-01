import logging
from typing import Any
from typing import Dict


logger = logging.getLogger(__name__)


def dirty_set_all(target: Any, attributes: Dict[str, Any]) -> bool:
    dirty = False
    for key, value in attributes.items():
        if not hasattr(target, key):
            raise ValueError(f"Type in attribute {key} against target {target}")
        old_value = getattr(target, key)
        if old_value != value:
            setattr(target, key, value)
            logger.info(f"DIRTY!!!!! {target} - {key} old {old_value} new {value}")
            dirty = True

    return dirty
