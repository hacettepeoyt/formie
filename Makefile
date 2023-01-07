.PHONY: run clean

run: .venv .formie-secret-key formie.db
	source .venv/bin/activate && \
	SECRET_KEY="$$(cat .formie-secret-key)" SQLALCHEMY_DATABASE_URI="sqlite:///$(PWD)/formie.db" FLASK_APP="formie" FLASK_DEBUG=1 python -m flask run

clean:
	rm -rf .venv .formie-secret-key formie.db

.venv: requirements.txt
	python3 -m venv .venv
	source .venv/bin/activate && pip install -U -r requirements.txt

.formie-secret-key:
	head -c 32 /dev/urandom | base64 > .formie-secret-key

%.db: .venv .formie-secret-key
	source .venv/bin/activate && \
	SECRET_KEY="$$(cat .formie-secret-key)" SQLALCHEMY_DATABASE_URI="sqlite:///$(PWD)/$@" python setup-db.py 0
