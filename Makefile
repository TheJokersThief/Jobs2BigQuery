.PHONY: test coverage lint docs clean dev install help export_conf create_pubsub_topic deploy_to_gfunctions

PROJECT_NAME = jobs2bigquery
PROJECT_ID ?= example-project

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

ensure-poetry:
	@if ! [ -x $(command -v poetry) ]; then \
		echo "Please install poetry (e.g. pip install poetry)"; \
		exit 1; \
	fi

lint: ensure-poetry  ## Lint files for common errors and styling fixes
	poetry check
	poetry run flake8 --ignore F821,W504 $(project)

test: ensure-poetry lint  ## Run unit tests
	poetry run pytest tests --cov=$(project) --strict tests

coverage: ensure-poetry test  ## Output coverage stats
	poetry run coverage report -m
	poetry run coverage html
	@echo "coverage report: file://`pwd`/htmlcov/index.html"

clean:
	find . -name '*.pyc' -delete
	find . -name __pycache__ -delete
	rm -rf .coverage dist build htmlcov *.egg-info

dev: ensure-poetry clean  ## Install project and dev dependencies
	poetry install

install: ensure-poetry clean  ## Install project without dev dependencies
	poetry install --no-dev

export_conf:  ## Export the poetry lockfile to requirements.txt
	poetry export -f requirements.txt --output requirements.txt --without-hashes

create_pubsub_topic:
ifeq ($(shell gcloud --project=iamevan-me pubsub topics list --filter="name~trigger-${PROJECT_NAME}" | wc -l), 0)
	gcloud --project=${PROJECT_ID} pubsub topics create "trigger-${PROJECT_NAME}"
endif

deploy_to_gfunctions: create_pubsub_topic export_conf
	gcloud functions deploy ${PROJECT_NAME} --region europe-west1 --project ${PROJECT_ID} --runtime python38 --memory 256MB --entry-point execute_jobs2bigquery --trigger-topic "trigger-${PROJECT_NAME}" --timeout 540s --max-instances 1

publish: deploy_to_gfunctions  ## Publish project to google cloud functions
	@echo "Published"

add_job:  ## Adds a message to the pubsub topic, using the content in deploy/pubsub_payload.json
	gcloud pubsub topics publish "projects/${PROJECT_ID}/topics/trigger-${PROJECT_NAME}" --message='$(shell cat deploy/pubsub_payload.json)'
