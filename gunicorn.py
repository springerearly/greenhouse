# gunicorn.conf.py
 
command = ".venv/bin/gunicorn"
pythonpath = "code/greenhouse"
bind = "0.0.0.0:8000"
workers = 5