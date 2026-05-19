PYTHON ?= python3
APP_NAME := Kepler Path

.PHONY: install install-build run web mac-app server clean-build

install:
	$(PYTHON) -m pip install -r requirements.txt

install-build:
	$(PYTHON) -m pip install -r requirements.txt -r requirements-build.txt

run:
	$(PYTHON) main.py

web:
	$(PYTHON) -m pygbag --build --disable-sound-format-error main.py

mac-app:
	$(PYTHON) -m PyInstaller --noconfirm --windowed --name "$(APP_NAME)" --add-data "assets:assets" main.py

server:
	npm --prefix server start

clean-build:
	rm -rf build dist *.spec
