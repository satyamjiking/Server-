#!/usr/bin/env bash
# ensure executable (git + render) and run gunicorn
gunicorn main:app --bind 0.0.0.0:$PORT --workers 1 --threads 2
