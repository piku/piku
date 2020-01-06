VENV=./venv/bin/activate
BIN=piku-gateway

demo: $(VENV) ../piku.py
	cp ../piku.py .
	. $(VENV); pex . -r requirements.txt -c piku.py -o $(BIN) --python-shebang='#!/usr/bin/env python'
	rm piku.py

$(VENV): requirements.txt
	test -d venv || virtualenv venv
	. $(VENV); pip install -Ur requirements.txt
	touch $(VENV)

.PHONY: clean

clean:
	rm -rf $(BIN) venv
