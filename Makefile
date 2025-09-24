.PHONY: install run clean docker-build docker-run format

VENV ?= .venv
PYTHON ?= python3
PIP ?= $(VENV)/bin/pip

install: $(VENV)/bin/activate

$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(VENV)/bin/python -m kg_constructor $(ARGS)

format:
	$(VENV)/bin/python -m black src

clean:
	rm -rf $(VENV)

docker-build:
	docker build -t kg-constructor .

docker-run:
	docker run --rm --network host \
		-v $(PWD)/data/output:/app/data/output \
		-e VLLM_URL=$${VLLM_URL:-http://localhost:8000} \
		-e VLLM_API_KEY=$${VLLM_API_KEY:-} \
		kg-constructor $(ARGS)
