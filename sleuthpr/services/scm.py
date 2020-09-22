from typing import Dict, Optional, Any

from sleuthpr.models import Installation


class InstallationSource:
    def on_event(self, event: Dict, headers: Optional[Dict] = None):
        pass

    def get_installation(self, installation_id: Any) -> Optional[Installation]:
        pass

