#!/bin/bash

echo "Setting up WebODM Task API"

# Find the name of the WebODM Docker network
WEBODM_NETWORK=$(docker network ls --filter name=webodm --format "{{.Name}}")

if [ -z "$WEBODM_NETWORK" ]; then
    echo "Error: Could not find WebODM Docker network."
    echo "Make sure WebODM is running before setting up the Task API."
    exit 1
fi

echo "Found WebODM network: $WEBODM_NETWORK"

# Update the docker-compose file with the correct network name
sed -i "s/webodm-network/$WEBODM_NETWORK/g" docker-compose.taskapi.yml

# Build and start the Task API service
docker-compose -f docker-compose.taskapi.yml up -d

echo "WebODM Task API is now running on http://localhost:8899/docs"
echo "Try accessing these endpoints:"
echo "- http://localhost:8899/api/tasks/ownership"
echo "- http://localhost:8899/api/tasks/status"
echo "- http://localhost:8899/api/tasks/{task_id}/owner"
echo "- http://localhost:8899/api/tasks/{task_id}/check-access/{username}"
