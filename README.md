# formie

Open source form application made with pure HTML/CSS/JS. Needs minimal client-side JS for form creation.

## Setup

```sh
export SQLALCHEMY_DATABASE_URI="sqlite:///test.db"
export SECRET_KEY="fiesta"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 setup-db.py 0

# Run with:
source venv/bin/activate
FLASK_APP=formie FLASK_ENV=development flask run
```
