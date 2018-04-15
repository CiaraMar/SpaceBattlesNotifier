#!/bin/bash
DEV_PATH=/usr/src/app
docker stop sb_notifier
docker run --rm --name sb_notifier -it --net=host -v $(pwd):/$DEV_PATH sb_notif bash