#!/bin/bash

virtualenv .venv
./tools/with_venv.sh pip install --upgrade -r requirements.txt