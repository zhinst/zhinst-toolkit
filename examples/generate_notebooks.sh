#!/bin/bash
__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_np=${1:-"none"}

jupytext --sync ${__dir}/*.md

if [ "$run_np" == "run" ]
then
    jupytext --execute  ${__dir}/*.ipynb
fi
