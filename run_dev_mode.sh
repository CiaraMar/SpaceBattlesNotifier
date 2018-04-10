#!/bin/bash
DEV_PATH=/usr/src/app
docker run --rm --name sb_notifier -it --net=host -v $(pwd):/$DEV_PATH sb_notif bash