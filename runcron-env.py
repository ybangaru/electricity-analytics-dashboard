#!/bin/bash

source /home/ubuntu/electricity-analytics-dashboard/iexanalytics/bin/activate
cd /home/ubuntu/electricity-analytics-dashboard/
python /home/ubuntu/electricity-analytics-dashboard/get_latest_prices.py
python /home/ubuntu/electricity-analytics-dashboard/prices_to_db.py
python /home/ubuntu/electricity-analytics-dashboard/get_latest_volumes.py
python /home/ubuntu/electricity-analytics-dashboard/volumes_to_db.py