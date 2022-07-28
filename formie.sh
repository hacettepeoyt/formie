#!/usr/bin/env bash

source /etc/formie/config.sh

cd /opt/formie
FLASK_ENV="production" gunicorn --bind 127.0.0.1:5240 'formie:create_app()'
