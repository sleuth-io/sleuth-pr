from typing import Optional

from django.db.models import Q

from sleuthpr.models import ExternalUser
from sleuthpr.models import Installation


def get_or_create(
    installation: Installation,
    name: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    remote_id: Optional[str] = None,
):

    existing_user = ExternalUser.objects.filter(
        Q(installation=installation) & (Q(username=username) | Q(remote_id=remote_id) | Q(email=email))
    ).first()
    if not existing_user:
        return ExternalUser.objects.create(
            installation=installation,
            name=name,
            email=email,
            username=username,
            remote_id=remote_id,
        )
    else:
        changed = False
        if username and existing_user.username != username:
            existing_user.username = username
            changed = True
        elif email and existing_user.email != email:
            existing_user.email = email
            changed = True
        elif name and existing_user.name != name:
            existing_user.name = name
            changed = True
        elif remote_id and existing_user.remote_id != remote_id:
            existing_user.remote_id = remote_id
            changed = True
        if changed:
            existing_user.save()

        return existing_user
