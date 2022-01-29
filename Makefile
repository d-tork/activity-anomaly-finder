SHELL := bash
.ONESHELL:

URL = "https://kilthub.cmu.edu/ndownloader/files/24856766"

.PHONY: venv

all: r4.2.tar.bz2 extract venv

r4.2.tar.bz2:
	curl -sL $(URL) > $@
	# To do it all in one step, curl might need to -O (output to stdout)

extract: r4.2.tar.bz2
	tar -xjvf $< -C . r4.2/{file,email,device,logon}.csv
	# TODO: the braces syntax of searching for those files did NOT work on dolores

venv: requirements.txt
	python3 -m venv venv
	source venv/bin/activate
	python -m pip install -r requirements.txt
