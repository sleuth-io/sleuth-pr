# The code must flow

Shipping code takes too long, leading to knowledge staleness, increased merge conflicts, and failed deployments.
Sleuth PR is a pull request automation engine to keep developers in the flow and their code shipping.

#   Automate the boring dev bits

Sleuth PR is a pull request workflow automation engine to keep the code flowing.  
It allows a team to automate the boring, manual parts of their workflow so the 
developers can ship quicker, safer, and more frequently by staying in the flow.

## Features

* **Automate tasks like merging and updating** - Automate merges and other tasks, based on your team's unique requirements
* **Flexible rules engine** - Create rules that contain powerful expressions and actions to automate many tasks
* **Standalone or embed** - Run standalone as a GitHub action or embed in another Django application
* **Completely free** - Apache v2 license

## Quickstart

Sleuth PR can be ran in three modes: standalone, in CI (GitHub action), and embedded in another Django application.
The easiest to get started is to use Sleuth PR in CI, ideally as a GitHub action.

### Run as a Standalone GitHub App for development

Here is how to run Sleuth PR as a standalone application from source code:

1. Create a GitHub app with a private key
1. Copy `config/dev/env.template` to `config/dev/env` and change the values to those from the GitHub app
1. Run `make up` 
