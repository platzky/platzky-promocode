.PHONY: lint dev lint-check unit-tests coverage html-cov build build-frontend compile-translations update-translations

lint:
	poetry run black .
	poetry run ruff check --fix .

dev: lint
	poetry run pyright .

lint-check:
	poetry run black --check .
	poetry run ruff check .
	poetry run pyright .
	poetry run interrogate platzky_promocode/ --verbose

unit-tests:
	poetry run python -m pytest -v

coverage:
	poetry run coverage run --branch --source=platzky_promocode -m pytest -m "not skip_coverage"
	poetry run coverage report --fail-under=90
	poetry run coverage lcov

html-cov: coverage
	poetry run coverage html

build-frontend:
	cd frontend && npm install && npm run build

build: build-frontend compile-translations
	poetry build

compile-translations:
	poetry run pybabel compile -d platzky_promocode/locale

update-translations:
	poetry run pybabel extract -F babel.cfg -o messages.pot platzky_promocode/
	poetry run pybabel update -i messages.pot -d platzky_promocode/locale
