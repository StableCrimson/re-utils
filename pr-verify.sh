ruff check
read -p "Press enter to run unit tests."
pytest --cov src --cov-fail-under 90 --cov-report term-missing