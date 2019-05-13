#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")"; cd ..; pwd)"
echo "Building foveate_OpenGL Docker image..."
docker build -t foveate_ogl .
