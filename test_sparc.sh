#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run example
sparc generate examples/example_transcript.txt -n test_project

# Validate results
echo "Test complete! Check output/test_project for results."
