#!/bin/bash
bokeh serve resell_app.py --port $PORT --address 0.0.0.0 --allow-websocket-origin=*
