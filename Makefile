RUFF_VERSION := 0.17.3

.PHONY: format format-check

format:
	uvx ruff==$(RUFF_VERSION) format .

format-check:
	uvx ruff==$(RUFF_VERSION) format --check .
