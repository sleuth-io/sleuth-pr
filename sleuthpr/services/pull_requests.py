import logging
from typing import Dict

from dateutil import parser
from django.db import transaction

from sleuthpr.models import ExternalUser
from sleuthpr.models import Installation
from sleuthpr.models import PullRequest
from sleuthpr.models import PullRequestAssignee
from sleuthpr.models import PullRequestLabel
from sleuthpr.models import PullRequestReviewer
from sleuthpr.models import Repository
from sleuthpr.services import external_users

logger = logging.getLogger(__name__)


@transaction.atomic
def update(installation: Installation, repository: Repository, data: Dict):
    remote_id = data["number"]

    pr: PullRequest = repository.pull_requests.filter(remote_id=remote_id).first()
    if not pr:
        pr = PullRequest(repository=repository)

    created = parser.parse(data["created_at"])
    author = _get_user(installation, data["user"])
    pr.remote_id = remote_id
    pr.title = data["title"]
    pr.description = data.get("body")
    pr.url = data["html_url"]
    pr.on = created
    pr.author = author
    pr.source_branch_name = data["head"]["ref"]
    pr.base_branch_name = data["base"]["ref"]
    pr.save()

    pr.assignees.all().delete()
    for reviewer_data in data.get("assignees", []):
        person = _get_user(installation, reviewer_data)
        PullRequestAssignee.objects.create(user=person, pull_request=pr)

    pr.reviewers.all().delete()
    for reviewer_data in data.get("requested_reviewers", []):
        person = _get_user(installation, reviewer_data)
        PullRequestReviewer.objects.create(user=person, pull_request=pr)

    pr.labels.all().delete()
    for label_data in data.get("labels", []):
        PullRequestLabel.objects.create(pull_request=pr, value=label_data["name"])

    return pr


def _get_user(installation: Installation, data: Dict) -> ExternalUser:
    return external_users.get_or_create(
        installation=installation,
        username=data.get("login"),
        remote_id=data.get("id"),
        email=data.get("email"),
        name=data.get("name"),
    )
