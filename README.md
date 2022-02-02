## Greengrass Labs InfluxDBPublisher Component - `aws.greengrass.labs.telemetry.InfluxDBPublisher`

## Overview
This AWS IoT Greengrass component allows you to forward Greengrass telemetry to InfluxDB.
It has a dependency on the [aws.greengrass.labs.database.InfluxDB Greengrass component ](https://github.com/awslabs/aws-greengrass-labs-database-influxdb), which starts and provisions a managed InfluxDB instance.

At a high level, the component will do the following:

1. Pull down the [Nucleus Telemetry Emitter](https://docs.aws.amazon.com/greengrass/v2/developerguide/nucleus-emitter-component.html) component plugin, which publishes Greengrass System Telemetry data to the local pub/sub topic `$local/greengrass/telemetry` at a configurable rate.
2. Send a request to the IPC topic `greengrass/influxdb/token/request` (configurable) to retrieve InfluxDB credentials and metadata from `aws.greengrass.labs.database.InfluxDB`
3. Receive a message on the IPC topic `greengrass/influxdb/token/response` (configurable).
4. Use the retrieved credentials to connect to InfluxDB.
5. Set up a subscription to the `$local/greengrass/telemetry` topic and forward all telemetry messages to InfluxDB.

This component works together with the `aws.greengrass.labs.dashboard.InfluxDBGrafana`, `aws.greengrass.labs.database.InfluxDB` and `aws.greengrass.labs.dashboard.Grafana` components to persist and visualize Greengrass System Telemetry data.
The `aws.greengrass.labs.dashboard.InfluxDBGrafana` component automates the setup of Grafana with InfluxDB to provide a "one-click" experience, but this component still needs to be configured first before creation. See the `Setup` section below for instructions.
* [aws.greengrass.labs.database.InfluxDB](https://github.com/awslabs/aws-greengrass-labs-database-influxdb)
* [aws.greengrass.labs.dashboard.Grafana](https://github.com/awslabs/aws-greengrass-labs-dashboard-grafana)
* [aws.greengrass.labs.dashboard.InfluxDBGrafana](https://github.com/awslabs/aws-greengrass-labs-dashboard-influxdb-grafana)

## Configuration
* `TokenRequestTopic`- the topic to send a request to in order to retrieve InfluxDB credentials
  * (`string`)
  * default: `greengrass/influxdb/token/request`


* `TokenResponseTopic`- the topic to subscribe to in order to receive the response with InfluxDB credentials
  * (`string`)
  * default: `greengrass/influxdb/token/response`
  

* `accessControl` - [Greengrass Access Control Policy](https://docs.aws.amazon.com/greengrass/v2/developerguide/interprocess-communication.html#ipc-authorization-policies), required for InfluxDB secret retrieval over pub/sub.
  * A default `accessControl` policy allowing publish access to the `greengrass/influxdb/token/request` topic and subscribe access to the `greengrass/influxdb/token/response` has been included and requires no further configuration


## Setup
* This component requires no additional configuration, unless the request/response topics are modified in `aws.greengrass.labs.database.InfluxDB`
* When deployed, this component will automatically begin forwarding telemetry from the [Nucleus Telemetry Emitter component plugin](https://docs.aws.amazon.com/greengrass/v2/developerguide/nucleus-emitter-component.html).
  * Since the default publish interval for the Nucleus Telemetry Emitter is 60 seconds, you may want to configure that component during deployment to have a lower publish interval with a configuration update similar to the following (which sets it to 5 seconds). Note that smaller publish intervals may result in higher CPU usage on your device.
    ```
    {
    "telemetryPublishIntervalMs": "5000"
    }
    ```

### Prerequisites
1. Setup the GDK CLI, Greengrass, and `aws.greengrass.labs.database.InfluxDB` using [the instructions here](https://github.com/awslabs/aws-greengrass-labs-database-influxdb/blob/main/README.md#setup).

### Component Setup
2. Pull down the component in a new directory using the [GDK CLI](https://docs.aws.amazon.com/greengrass/v2/developerguide/install-greengrass-development-kit-cli.html).
    ```
   mkdir aws-greengrass-labs-telemetry-influxdbpublisher; cd aws-greengrass-labs-telemetry-influxdbpublisher
   gdk component init --repository aws-greengrass-labs-telemetry-influxdbpublisher
   ```
3. Use the [GDK CLI](https://docs.aws.amazon.com/greengrass/v2/developerguide/greengrass-development-kit-cli.html) to build the component to prepare for publishing.
   ```
   gdk component build
   ```
4. Use the [GDK CLI](https://docs.aws.amazon.com/greengrass/v2/developerguide/greengrass-development-kit-cli.html) to create a private component.
   ```
   gdk component publish
   ```
    
## Sending Custom Telemetry
* This component listens to all telemetry on the `$local/greengrass/telemetry` topic and forwards it to InfluxDB.
* You can also send your own custom telemetry to this topic from your own Greengrass component to have it forwarded to InfluxDB.
  * See the [local pub/sub documentation to learn more](https://docs.aws.amazon.com/greengrass/v2/developerguide/ipc-publish-subscribe.html).
* The component expects messages to consist of a JSON array in the following format. [See the Nucleus Emitter output](https://docs.aws.amazon.com/greengrass/v2/developerguide/nucleus-emitter-component.html#nucleus-emitter-component-output-data) for a full example.
    ```
    [{
    "A": "<Aggregation Type>",
    "N": "<Metric Name>",
    "NS": "<Metric Namespace>",
    "TS": <Metric Timestamp>,
    "U":  "<Metric Unit>",
    "V":  <Metric Value>
  },
  ...
  ]
    ```
  * `A` - The aggregation type for the metric. 
  * `N`- The name of the metric. 
  * `NS`- The metric namespace. 
  * `TS`- The timestamp of when the data was gathered. (ms since Unix Epoch start time) 
  * `U` - The unit of the metric value. 
  * `V` - The metric value.
## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.

## Troubleshooting
* Troubleshooting for this component is mainly the same as for `aws.greengrass.labs.database.InfluxDB`. Please see [its troubleshooting guide here.](https://github.com/awslabs/aws-greengrass-labs-database-influxdb/blob/main/README.md#troubleshooting)
