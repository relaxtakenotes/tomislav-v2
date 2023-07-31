#!/bin/bash
(cd /home/steam/tomislav-v2/tomislav-slave/; gunicorn -w 4 -b 0.0.0.0:8000 --timeout 600 'app:app')