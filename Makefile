.PHONY: help rebuild-index lint format lint-py lint-js format-py format-js check-format-py format docs build

# Help system from https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

pyenv: ## Install and setup local py env
	python3.8 -m venv venv
	venv/bin/pip install -r requirements.txt

tunnel: ## Set up a public ngrok tunnel to your dev instance for webhook testing
ifeq (, $(shell which ngrok))
	@echo "Install ngrok.  On linux, run 'sudo snap install ngrok'.  Then, set the authtoken"
	@echo "via 'ngrok authtoken TOKEN' using the auth token in the ngrok account."
else
	timeout --foreground --preserve-status 60m ngrok http -hostname=pr-dev.ngrok.io 8000
endif


clean: pyenv ## Clean the project and set everything up

up: docs ## Start the application for development
	bin/run-web-dev.sh


lint: ## Run Python linters
	flake8 app
	flake8 sleuthpr
	pylint app
	pylint sleuthpr

check-format: lint ## Check Python code formatting
	black app --check --target-version py38
	black sleuthpr --check --target-version py38
	reorder-python-imports --py38-plus `find sleuthpr -name "*.py"`
	reorder-python-imports --py38-plus `find app -name "*.py"`

docs: ## Serve the docs
	mkdocs serve -a localhost:8035


build: ## Build the docker container
	docker build -t sleuthpr-dev --build-arg VERSION=`python setup.py --version` .

format: ## Format Python code
	black app --target-version py38
	black sleuthpr --target-version py38
	reorder-python-imports --py38-plus `find sleuthpr -name "*.py"` || black sleuthpr --target-version py38
	reorder-python-imports --py38-plus `find app -name "*.py"` || black app --target-version py38
