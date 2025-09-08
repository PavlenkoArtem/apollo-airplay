#!/bin/bash
cd /home/apollo/UxPlay/build
#DISPLAY=:0 unclutter -idle 0
GST_PLUGIN_PATH=/usr/lib/gstreamer-1.0 DISPLAY=:0 /usr/local/bin/uxplay -bt709 -s 1280x720  -fps 30 -o -fs -vd v4l2h264dec -nh -v4l2 -avdec -n Apollo -reg
