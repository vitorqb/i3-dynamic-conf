.PHONY: venv package test

activate_venv = . ./venv/bin/activate

venv:
	rm -rf venv
	virtualenv3 venv
	$(activate_venv) && pip install -r requirements.txt

package:
	$(eval REF=$(shell git describe --tags))
	$(eval TARFILE=./packages/i3-dynamic-conf-${REF}.tar.gz)
	rm -rf "$(TARFILE)"
	mkdir -p ./packages
	tar\
	    --exclude ./packages\
	    --exclude ./venv\
	    --exclude __pycache__\
	    -vzcf "$(TARFILE)" \
	    ./*

test:
	$(activate_venv) && python -m unittest discover -p 'test_*'
