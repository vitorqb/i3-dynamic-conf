.PHONY: venv

activate_venv = . ./venv/bin/activate

venv:
	rm -rf venv
	virtualenv3 venv
	$(activate_venv) && pip install -r requirements.txt
