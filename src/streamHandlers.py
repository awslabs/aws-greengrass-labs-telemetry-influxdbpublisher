# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import influxdb_client
from datetime import datetime, timezone
from distutils.util import strtobool

import awsiot.greengrasscoreipc.client as client
from awsiot.greengrasscoreipc.model import (
    SubscriptionResponseMessage
)

REQUEST_ID = 'aws-greengrass-labs-telemetry-influxdbpublisher'

class InfluxDBDataStreamHandler(client.SubscribeToTopicStreamHandler):
    def __init__(self):
        super().__init__()
        self.influxdb_parameters = {}

    def on_stream_event(self, event: SubscriptionResponseMessage) -> None:
        """
        When we receive a message over IPC on the token response topic, load in the InfluxDB parameters

        Parameters
        ----------
            event(SubscriptionResponseMessage): The received IPC message

        Returns
        -------
            None
        """
        try:
            if ('request_id' in event.json_message.message):
                if event.json_message.message['request_id'] == REQUEST_ID:
                    self.influxdb_parameters = event.json_message.message
                    if len(self.influxdb_parameters) == 0:
                        raise ValueError("Retrieved Influxdb parameters are empty!")
        except Exception:
            logging.error('Failed to load telemetry event JSON!', exc_info=True)
            exit(1)

    def on_stream_error(self, error: Exception) -> bool:
        """
        Log stream errors but keep the stream open.

        Parameters
        ----------
            error(Exception): The exception we see as a result of the stream error.

        Returns
        -------
            False(bool): Return False to keep the stream open.
        """
        logging.error("Received a stream error.", exc_info=True)
        return False  # Return True to close stream, False to keep stream open.

    def on_stream_closed(self) -> None:
        """
        Handle the stream closing.

        Parameters
        ----------
            None

        Returns
        -------
            None
        """
        logging.info('Subscribe to InfluxDB response topic stream closed.')


class TelemetryStreamHandler(client.SubscribeToTopicStreamHandler):
    def __init__(self, influxdb_parameters):
        super().__init__()
        self.influxdb_parameters = influxdb_parameters

        skip_tls_verify = bool(strtobool(self.influxdb_parameters['InfluxDBSkipTLSVerify']))
        if skip_tls_verify:
            import urllib3
            # Necessary to suppress warning for self-signed certs
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        ssl_verify = not skip_tls_verify

        self.influxDBclient = influxdb_client.InfluxDBClient(
            url="{}://{}:{}".format(
                self.influxdb_parameters['InfluxDBServerProtocol'],
                self.influxdb_parameters['InfluxDBInterface'],
                self.influxdb_parameters['InfluxDBPort']
            ),
            token=self.influxdb_parameters['InfluxDBToken'],
            org=self.influxdb_parameters['InfluxDBOrg'],
            verify_ssl=ssl_verify
        )
        self.write_client = self.influxDBclient.write_api(write_options=influxdb_client.client.write_api.SYNCHRONOUS)
        logging.info("Successfully initialized InfluxDB Client on {}://{}:{}".format(
            self.influxdb_parameters['InfluxDBServerProtocol'],
            self.influxdb_parameters['InfluxDBInterface'],
            self.influxdb_parameters['InfluxDBPort'])
        )

    def on_stream_event(self, event: SubscriptionResponseMessage) -> None:
        """
        When we receive a message over IPC on the local telemetry topic, publish the telemetry event to InfluxDB

        Parameters
        ----------
            event(SubscriptionResponseMessage): The received IPC message

        Returns
        -------
            None
        """
        try:
            if event is None:
                raise ValueError("Received telemetry event was None!")
            message = str(event.binary_message.message, "utf-8")
            jsonString = json.loads(message)
            if (len(jsonString) == 0):
                raise ValueError("Retrieved telemetry is empty!")
            parsedPoints = self.createPoints(jsonString)
            self.write_client.write(
                bucket=self.influxdb_parameters['InfluxDBBucket'],
                org=self.influxdb_parameters['InfluxDBOrg'],
                record=parsedPoints
            )
        except Exception:
            logging.error("Received an error while writing to InfluxDB.", exc_info=True)
            exit(1)

    def on_stream_error(self, error: Exception) -> bool:
        """
        Log stream errors but keep the stream open.

        Parameters
        ----------
            error(Exception): The exception we see as a result of the stream error.

        Returns
        -------
            False(bool): Return False to keep the stream open.
        """
        logging.error("Received a stream error.", exc_info=True)
        return False  # Return True to close stream, False to keep stream open.

    def on_stream_closed(self) -> None:
        """
        Handle the stream closing.

        Parameters
        ----------
            None

        Returns
        -------
            None
        """
        logging.info('Subscribe to Greengrass telemetry topic stream closed.')

    def createPoints(self, jsonString):
        """
        Helper function to create an array of InfluxDB Points to publish to InfluxDB

        Parameters
        ----------
            jsonString(dict): The telemetry event JSON

        Returns
        -------
            influxdb_client.Point
        """
        points = []
        for metric in jsonString:

            # Must convert to UTC for InfluxDB
            p = influxdb_client.Point(metric["N"]).tag("NS", metric["NS"]) \
                .tag("U", metric["U"]) \
                .tag("A", metric["A"]) \
                .field("V", metric["V"]) \
                .time(datetime.fromtimestamp(metric["TS"]/1000.0, tz=timezone.utc))
            points.append(p)
        return points
