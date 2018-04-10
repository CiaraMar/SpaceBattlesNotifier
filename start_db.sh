#!/bin/bash
source create_user_info.sh
docker run --rm --name $MONGO_DB_NAME -p 27017:27017 -p 27018:27018 -p 27019:27019 -v $(pwd)/mongo/datadir:/data/db -d mongo

docker run -d --rm \
    --name mongo-express \
    --link $MONGO_DB_NAME:mongo \
    -p 8081:8081 \
    -e ME_CONFIG_OPTIONS_EDITORTHEME="ambiance" \
    -e ME_CONFIG_BASICAUTH_USERNAME="$MONGO_USER_NAME" \
    -e ME_CONFIG_BASICAUTH_PASSWORD="$MONGO_PW" \
    mongo-express