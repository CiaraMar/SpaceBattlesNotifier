#!/bin/bash
DEV_PATH=/usr/src/app
docker stop sb_notifier
docker run -d --rm --name sb_notifier --net=host -v $(pwd):/$DEV_PATH sb_notif