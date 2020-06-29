#!/usr/bin/env bash

if [[ ! -f ./.pypirc ]] ; then
    echo 'File "./.pypirc" is missing, aborting.'
    exit
fi

python setup.py sdist bdist_wheel
python -m twine upload --config ./.pypirc dist/*