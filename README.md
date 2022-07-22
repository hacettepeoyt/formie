# formie

Open source form application made with pure HTML/CSS/JS. Needs minimal client-side JS for form creation.

## Setup

```sh
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 setup-db.py

# Run with:
source venv/bin/activate
FLASK_APP=formie FLASK_ENV=development SQLALCHEMY_DATABASE_URI="sqlite:///test.db" SECRET_KEY="fiesta" flask run
```
