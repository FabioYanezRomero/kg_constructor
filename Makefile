.PHONY: install run clean docker-build docker-run format

VENV ?= .venv
PYTHON ?= $(shell for c in python3.13 python3.12 python3.11 python3 python; do \
	command -v $$c >/dev/null 2>&1 || continue; \
	$$c -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1 && { echo $$c; exit 0; }; \
done; echo python3)
PIP ?= $(VENV)/bin/pip

install: $(VENV)/bin/activate
	$(PYTHON) -c 'import sys; sys.exit("Python 3.11+ is required for this project.") if sys.version_info < (3, 11) else None'
	$(PIP) install -e ".[dev]"

$(VENV)/bin/activate:
	$(PYTHON) -c 'import sys; sys.exit("Python 3.11+ is required for this project.") if sys.version_info < (3, 11) else None'
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

run:
	$(VENV)/bin/kgb $(ARGS)

format:
	$(VENV)/bin/python -m black kgb

clean:
	rm -rf $(VENV)

docker-build:
	docker build -t kg-constructor .

docker-run:
	docker run --rm --network host \
		-v $(PWD)/data/output:/app/data/output \
		-v $(PWD)/data/legal:/app/data/legal \
		-e VLLM_URL=$${VLLM_URL:-http://localhost:8000} \
		-e VLLM_API_KEY=$${VLLM_API_KEY:-} \
		kg-constructor $(ARGS)


docker-start:
	docker run -it --rm --network host \
		-v $(PWD):/app \
		--entrypoint bash \
		kg-constructor

docker-dev:
	docker run -d --name kg-dev --network host \
		-v $(PWD):/app \
		--entrypoint sleep \
		kg-constructor infinity

docker-stop:
	docker stop kg-dev && docker rm kg-dev
