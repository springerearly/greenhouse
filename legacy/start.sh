#!/bin/bash
.venv/bin/python code/greenhouse/manage.py collectstatic --noinput
.venv/bin/python code/greenhouse/manage.py my_custom_startup_command
.venv/bin/python .venv/bin/gunicorn --config gunicorn.py greenhouse.wsgi
