#!/bin/bash

set -e

docker run --rm -it --name pgarrow-postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres
