.PHONY: install dev test test-cov docker clean

install:
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov httpx

dev:
	uvicorn main:app --reload --port 8001

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=app --cov-report=term-missing

docker:
	docker-compose up -d --build

clean:
	docker-compose down -v
