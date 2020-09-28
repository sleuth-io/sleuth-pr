import logging
from typing import Any
from typing import Dict
from typing import Tuple

from dateutil import parser
from django.db import transaction

from sleuthpr.models import ExternalUser
from sleuthpr.models import Installation
from sleuthpr.models import PullRequest
from sleuthpr.models import PullRequestAssignee
from sleuthpr.models import PullRequestLabel
from sleuthpr.models import PullRequestReviewer
from sleuthpr.models import Repository
from sleuthpr.models import RepositoryIdentifier
from sleuthpr.services import checks
from sleuthpr.services import external_users
from sleuthpr.services import installations
from sleuthpr.services import pull_requests
from sleuthpr.services import repositories
from sleuthpr.services import rules
from sleuthpr.triggers import PR_CREATED
from sleuthpr.triggers import PR_UPDATED

logger = logging.getLogger(__name__)


def on_check_suite_requested(
    remote_id: str, repository_id: RepositoryIdentifier, data: Dict
):
    _update_attached_pull_requests(data, remote_id, repository_id)


def on_check_run(remote_id: str, repository_id: RepositoryIdentifier, data: Dict):
    _update_attached_pull_requests(data, remote_id, repository_id)


def on_push(remote_id: str, repository_id: RepositoryIdentifier, data: Dict):
    if "refs/heads/master" == data["ref"]:
        installation = installations.get(remote_id)
        repo = installation.repositories.filter(
            full_name=repository_id.full_name
        ).first()
        files = {}
        for commit in data["commits"]:
            for action in ("modified", "added", "removed"):
                for file in commit[action]:
                    files[file] = action

        if files.get(".sleuth/rules.yml"):
            logger.info("Push contained a rules file change, refreshing")
            repositories.refresh_rules(installation, repo)

        logger.info("Got a master push")
    else:
        logger.info("Not a master push")


def on_pr_created(remote_id: str, repository_id: RepositoryIdentifier, pr_data: Dict):
    installation = installations.get(remote_id)
    repo = installation.repositories.filter(full_name=repository_id.full_name).first()
    pr = _update_pull_request_and_process(installation, repo, pr_data)


def on_pr_updated(remote_id: str, repository_id: RepositoryIdentifier, pr_data: Dict):
    installation = installations.get(remote_id)
    repo = installation.repositories.filter(full_name=repository_id.full_name).first()
    _update_pull_request_and_process(installation, repo, pr_data)


def on_repositories_added(installation_id, data):
    installation = installations.get(installation_id)
    if data["repository_selection"] == "all":
        repos = installation.client.get_repositories()
        repositories.set_repositories(installation, repos)
    else:
        repos = [
            RepositoryIdentifier(full_name=repo["full_name"], remote_id=repo["id"])
            for repo in data["repositories_added"]
        ]
        repositories.add(installation, repos)


def on_repositories_removed(installation_id, data):
    installation = installations.get(installation_id)
    if data["repository_selection"] == "all":
        repos = installation.client.get_repositories()
        repositories.set_repositories(installation, repos)
    else:
        repos = [
            RepositoryIdentifier(full_name=repo["full_name"], remote_id=repo["id"])
            for repo in data["repositories_removed"]
        ]
        repositories.remove(installation, repos)


def on_installation_created(installation_id, data):
    target_type = data["installation"]["target_type"]
    target_id = data["installation"]["target_id"]
    repos = [
        RepositoryIdentifier(full_name=repo["full_name"], remote_id=repo["id"])
        for repo in data["repositories"]
    ]
    installations.create(
        remote_id=installation_id,
        target_type=target_type,
        target_id=target_id,
        repository_ids=repos,
        provider="github",
    )


def _update_pull_request_and_process(
    installation: Installation, repository: Repository, data: Dict
):
    pr, was_changed = _update_pull_request(installation, repository, data)
    if was_changed:
        pull_requests.on_updated(installation, repository, pr)
    return pr


@transaction.atomic
def _update_pull_request(
    installation: Installation, repository: Repository, data: Dict
) -> Tuple[PullRequest, bool]:
    remote_id = data["number"]

    pr: PullRequest = repository.pull_requests.filter(remote_id=remote_id).first()
    if not pr:
        pr = PullRequest(repository=repository)

    is_dirty = _dirty_set_all(
        pr,
        dict(
            remote_id=str(remote_id),
            source_branch_name=data["head"]["ref"],
            source_sha=data["head"]["sha"],
            base_branch_name=data["base"]["ref"],
        ),
    )

    if is_dirty:
        pr.save()

    if "title" not in data:
        return pr, is_dirty

    is_dirty = (
        _dirty_set_all(
            pr,
            dict(
                title=data["title"],
                description=data.get("body"),
                url=data["html_url"],
                on=parser.parse(data["created_at"]),
                author=_get_user(installation, data["user"]),
                draft=data["draft"],
                merged=data["merged"],
                mergeable=data["mergeable"] or False,
                rebaseable=data["rebaseable"] or False,
            ),
        )
        | is_dirty
    )

    if is_dirty:
        pr.save()

    assignees = set()
    for assignee_data in data.get("assignees", []):
        assignees.add(_get_user(installation, assignee_data))
    existing_assignees = {person.user.remote_id for person in pr.assignees.all()}
    if {str(person.remote_id) for person in assignees} != existing_assignees:
        pr.assignees.all().delete()
        for assignee_data in data.get("assignees", []):
            person = _get_user(installation, assignee_data)
            PullRequestAssignee.objects.create(user=person, pull_request=pr)
        is_dirty = True
        logger.info(f"DIRTY!!!!! assignees old {existing_assignees} new {assignees}")

    reviewers = set()
    for reviewer_data in data.get("requested_reviewers", []):
        reviewers.add(_get_user(installation, reviewer_data))
    existing_reviewers = {person.user.remote_id for person in pr.reviewers.all()}
    if {str(reviewer.remote_id) for reviewer in reviewers} != existing_reviewers:
        pr.reviewers.all().delete()
        for reviewer in reviewers:
            PullRequestReviewer.objects.create(user=reviewer, pull_request=pr)
        is_dirty = True
        logger.info(f"DIRTY!!!!! reviewers old {existing_reviewers} new {reviewers}")

    existing_labels = {label.value for label in pr.labels.all()}
    labels = {label_data["name"] for label_data in data.get("labels", [])}

    if labels != existing_labels:
        pr.labels.all().delete()
        for label_name in labels:
            PullRequestLabel.objects.create(pull_request=pr, value=label_name)
        logger.info(f"DIRTY!!!!! labels old {existing_labels} new {labels}")
        is_dirty = True

    return pr, is_dirty


def _dirty_set_all(target: Any, attributes: Dict[str, Any]) -> bool:
    dirty = False
    for key, value in attributes.items():
        if not hasattr(target, key):
            raise ValueError(f"Type in attribute {key} against target {target}")
        if getattr(target, key) != value:
            setattr(target, key, value)
            logger.info(f"DIRTY!!!!! {key} old {getattr(target, key)} new {value}")
            dirty = True

    return dirty


def _update_attached_pull_requests(data, remote_id, repository_id):
    installation = installations.get(remote_id)
    repository = repositories.get(installation, repository_id)
    for pr_data in data["pull_requests"]:
        _update_pull_request_and_process(installation, repository, pr_data)


def _get_user(installation: Installation, data: Dict) -> ExternalUser:
    return external_users.get_or_create(
        installation=installation,
        username=data.get("login"),
        remote_id=data.get("id"),
        email=data.get("email"),
        name=data.get("name"),
    )
