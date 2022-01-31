SHELL := bash
.ONESHELL:

URL = "https://kilthub.cmu.edu/ndownloader/files/24856766"

.PHONY: venv

all: download venv

download: r4.2.tar.bz2 r4.2 link

r4.2.tar.bz2:
	curl -sL $(URL) > $@

r4.2: r4.2.tar.bz2
	# will still keep them in a folder 'r4.2'
	tar -xjvf $< -C . --files-from files_to_extract.txt

link: r4.2
	# Create links to data files in current directory
	for filename in r4.2/*.csv; do
		ln -s filename .

venv: requirements.txt
	python3 -m venv venv
	source venv/bin/activate
	python -m pip install -r requirements.txt
