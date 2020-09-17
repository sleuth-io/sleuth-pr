.PHONY: help rebuild-index lint format lint-py lint-js format-py format-js check-format-py

# Help system from https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

pyenv: ## Install and setup local py env
	python3.8 -m pip install pipenv
	pipenv install --keep-outdated --dev

tunnel: ## Set up a public ngrok tunnel to your dev instance for webhook testing
ifeq (, $(shell which ngrok))
	@echo "Install ngrok.  On linux, run 'sudo snap install ngrok'.  Then, set the authtoken"
	@echo "via 'ngrok authtoken TOKEN' using the auth token in the ngrok account."
else
	timeout --foreground --preserve-status 60m ngrok http -hostname=pr-dev.ngrok.io 8000
endif

up: ## Start the application for development
	bin/run-web-dev.sh

