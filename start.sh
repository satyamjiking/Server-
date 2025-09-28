#!/usr/bin/env bash
python3 main.py &
gunicorn main:app --bind 0.0.0.0:$PORT
