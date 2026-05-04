VENV = .venv
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest
TIMEOUT = 60

.PHONY: test test-unit test-all clean

venv: $(VENV)/bin/activate

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install -q -r fastapi-demo/requirements.txt -r fastapi-demo/test_requirements.txt
	$(PIP) install -q -r llm-rag-demo/requirements.txt pytest pytest-asyncio pytest-timeout pytest-cov httpx

test: test-unit test-all
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "make test complete!"
	@echo ""
	@echo "Services:"
	@printf "  LLM RAG Demo:  "; curl -sf http://localhost:8001/health > /dev/null 2>&1 && echo "http://localhost:8001/docs" || echo "not running"
	@printf "  FastAPI Demo:  "; curl -sf http://localhost:8000/health > /dev/null 2>&1 && echo "http://localhost:8000/docs" || echo "not running"
	@printf "  Airflow UI:    "; curl -sf http://localhost:8080/health > /dev/null 2>&1 && echo "http://localhost:8080" || echo "not running"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test-unit: venv
	@echo ""
	@echo "━━━ fastapi-demo unit tests + coverage ━━━"
	cd fastapi-demo && ../$(PYTEST) tests/ -v --timeout=$(TIMEOUT) --cov=app --cov-report=term-missing
	@echo ""
	@echo "━━━ llm-rag-demo unit tests + coverage ━━━"
	cd llm-rag-demo && ../$(PYTEST) tests/ -v --timeout=$(TIMEOUT) --cov=app --cov-report=term-missing

test-all:
	@echo ""
	@echo "━━━ Docker integration tests ━━━"
	bash test_all.sh --start

clean:
	bash test_all.sh --clean
	rm -rf $(VENV)
