VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
CFG=config/config.yaml

.PHONY: setup install validate embed umap cluster axis_judge axis_embed all clean

setup:
	python3 -m venv $(VENV)
	$(PIP) install -U pip

install:
	$(PIP) install -r requirements.txt

validate:
	$(PY) scripts/00_validate_input.py --config $(CFG)

embed:
	$(PY) scripts/01_embed.py --config $(CFG)

umap:
	$(PY) scripts/02_umap.py --config $(CFG)

cluster:
	$(PY) scripts/03_cluster.py --config $(CFG)

axis_judge:
	$(PY) scripts/10_axis_score_judge.py --model $$OPENROUTER_MODEL

axis_embed:
	$(PY) scripts/11_axis_score_embedding.py

all: validate embed umap cluster

clean:
	rm -rf outputs data/processed
