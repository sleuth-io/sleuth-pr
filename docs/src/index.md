#   Automate pull requests

Sleuth PR is a pull request workflow automation engine to keep the code flowing.  
It allows a team to automate the boring, manual parts of their workflow so the 
developers can ship quicker, safer, and more frequently.

## Features

* **Automate boring pull request tasks** - Automate merges and other tasks, based on your team's unique requirements
* **Flexible rules engine** - Create rules that contain powerful expressions and actions to automate many tasks
* **Standalone or embed** - Run standalone as a GitHub action or embed in another Django application
* **Completely free** - Apache v2 license

## Quickstart

Sleuth PR can be ran in three modes: standalone, in CI (GitHub action), and embedded in another Django application.
The easiest to get started is to use Sleuth PR in CI, ideally as a GitHub action.

### Run as a GitHub action

1. Create a GitHub action file, say `.github/workflows/sleuth-pr.yml`, to trigger Sleuth PR:
{% raw %}
```
name: Automations

on: [push, pull_request, pull_request_review, check_run]

jobs:
  run-sleuth-pr:
    runs-on: ubuntu-latest
    steps:
    - uses: docker://mrdonbrown/sleuth-pr-dev:latest
      env:
        GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
```
{% endraw %}
1. Create the Sleuth PR rules file in `.sleuth/rules.yml`. Here is a simple rule that updates pull requests when
 their base branch changes:
```
rules:
  - update_if_dirty:
      description: "Update pull requests if their base branch changes"
      triggers:
        - base_branch_updated
      actions:
        - update_pull_request_base
```

## How it works

Rules are composed of optional [triggers](triggers/), [conditions](conditions/), and [actions](actions/).  How triggers are
 prompted depends on
 how
 Sleuth PR
 is executed. If it is executed as a GitHub Action, then the action name is mapped to the most appropriate trigger
  and any rules contain the matching trigger are evaluated. If Sleuth PR is executed as a GitHub App, Sleuth PR will
   receive a webhook from GitHub and will match the event to the appropriate trigger.
   
For more information about what triggers, conditions, and actions are available, see the links on the left.