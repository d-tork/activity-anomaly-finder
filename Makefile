SHELL := bash
.ONESHELL:

URL = "https://kilthub.cmu.edu/ndownloader/files/24856766"

.PHONY: venv

all: r4.2.tar.bz2 extract venv

r4.2.tar.bz2:
	curl -sL $(URL) > $@

extract: r4.2.tar.bz2
	tar -xjvf $< -C . --files-from files_to_extract.txt

venv: requirements.txt
	python3 -m venv venv
	source venv/bin/activate
	python -m pip install -r requirements.txt
