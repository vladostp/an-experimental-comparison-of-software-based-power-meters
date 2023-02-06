#!/usr/bin/env bash

maxfrequency=$(lscpu -b -p=MAXMHZ | tail -n -1 | cut -d . -f 1 | cut -d , -f 1)
minfrequency=$(lscpu -b -p=MINMHZ | tail -n -1 | cut -d . -f 1 | cut -d , -f 1)
basefrequency=$(lscpu | grep "Model name" | cut -d @ -f 2 | cut -d G -f 1)
basefrequency=$(expr ${basefrequency}\*1000 | bc | cut -d . -f 1 | cut -d , -f 1)

cat  <<END >./smartwatts_config.json
{
  "verbose": true,
  "stream": true,
  "input": {
      "puller": {
      "model": "HWPCReport",
      "type": "mongodb",
      "uri": "mongodb://mongodb",
      "db": "db_sensor",
      "collection": "report_0"
    }
  },
  "output": {
      "pusher_power": {
      "type": "mongodb",
      "uri": "mongodb://mongodb",
      "db": "smartwatts",
      "collection": "power"
    }
  },
  "cpu-frequency-base": $basefrequency,
  "cpu-frequency-min": $minfrequency,
  "cpu-frequency-max": $maxfrequency,
  "cpu-error-threshold": 2.0,
  "disable-dram-formula": false,
  "sensor-report-sampling-interval": 1000
}
END
