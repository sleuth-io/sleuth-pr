import logging
from typing import Dict
from typing import Tuple

from marshmallow import fields
from marshmallow import Schema
from marshmallow import validate

from sleuthpr.models import Action
from sleuthpr.models import ActionType
from sleuthpr.models import CheckStatus
from sleuthpr.models import MergeMethod
from sleuthpr.models import PullRequest


logger = logging.getLogger(__name__)


class MergePullRequestActionType(ActionType):
    def __init__(self):
        super().__init__(
            key="merge_pull_request",
            label="Merge the pull request",
            parameters=MergePullRequestActionSchema(),
            conditions=["draft=false", "merged=false", "closed=false"],
        )

    def execute(self, action: Action, context: Dict) -> Tuple[CheckStatus, str]:
        pull_request: PullRequest = context["pull_request"]
        if pull_request.merged or not pull_request.mergeable:
            logger.info("PR cannot be merged, skipping merge")
            return CheckStatus.FAILURE, "Pull request was not mergeable"

        new_sha = action.rule.repository.installation.client.merge(
            pull_request.repository,
            int(pull_request.remote_id),
            commit_title=action.parameters["commit_title"],
            commit_message=action.parameters["commit_message"],
            method=MergeMethod(action.parameters["merge_method"]),
            sha=pull_request.source_sha,
        )
        return CheckStatus.SUCCESS, f"Pull request merged successfully in {new_sha}"


class MergePullRequestActionSchema(Schema):
    commit_title = fields.Str(description="The commit title")
    commit_message = fields.Str(description="The commit message")
    merge_method = fields.Str(
        description="How the merge will happen",
        validate=validate.OneOf(MergeMethod.values),
        default=MergeMethod.MERGE.value,
    )
