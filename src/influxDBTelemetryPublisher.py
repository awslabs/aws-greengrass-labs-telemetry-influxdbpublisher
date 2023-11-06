# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import concurrent.futures
import time
import logging
import argparse

import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.model import (
    PublishToTopicRequest,
    PublishMessage,
    JsonMessage,
    SubscribeToTopicRequest,
    UnauthorizedError
)
import streamHandlers

logging.basicConfig(level=logging.INFO)

# Fixed topic for Greengrass local telemetry
telemetry_topic = "$local/greengrass/telemetry"
TIMEOUT = 10

influxdb_parameters = {}


def parse_arguments() -> argparse.Namespace:
    """
    Parse arguments.

    Parameters
    ----------
        None

    Returns
    -------
        args(Namespace): Parsed arguments
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--subscribe_topic", type=str, required=True)
    parser.add_argument("--publish_topic", type=str, required=True)
    return parser.parse_args()


def publish_token_request(ipc_publisher_client, publish_topic) -> None:
    """
    Publish a token request to the specified publish topic.

    Parameters
    ----------
        ipc_publisher_client(awsiot.greengrasscoreipc.client): the Greengrass IPC client
        publish_topic(str): the topic to publish the request on

    Returns
    -------
        None
    """

    request = PublishToTopicRequest()
    request.topic = publish_topic
    publish_message = PublishMessage()
    publish_message.json_message = JsonMessage(message={"action": "RetrieveToken",  "accessLevel": "RW", 'request_id': streamHandlers.REQUEST_ID})
    request.publish_message = publish_message
    publish_operation = ipc_publisher_client.new_publish_to_topic()
    try:
        publish_operation.activate(request)
        futureResponse = publish_operation.get_response()
        futureResponse.result(TIMEOUT)
    except concurrent.futures.TimeoutError as e:
        logging.error('Timeout occurred while publishing to topic: {}'.format(publish_topic), exc_info=True)
        raise e
    except UnauthorizedError as e:
        logging.error('Unauthorized error while publishing to topic: {}'.format(publish_topic), exc_info=True)
        raise e
    except Exception as e:
        logging.error('Exception while publishing to topic: {}'.format(publish_topic), exc_info=True)
        raise e


def retrieve_influxdb_params(publish_topic, subscribe_topic) -> str:
    """
    Subscribe to a token response topic and send a request to the token request topic
    in order to retrieve InfluxDB parameters.

    Parameters
    ----------
        publish_topic(str): the topic to publish the request on
        subscribe_topic(str): the topic to subscribe on to retrieve the response

    Returns
    -------
        influxdb_parameters(str): the retrieved parameters needed to connect to InfluxDB
    """
    # First, set up a subscription to the InfluxDB token response topic
    ipc_subscriber_client = awsiot.greengrasscoreipc.connect()
    request = SubscribeToTopicRequest()
    request.topic = subscribe_topic
    handler = streamHandlers.InfluxDBDataStreamHandler()
    subscriber_operation = ipc_subscriber_client.new_subscribe_to_topic(handler)
    future = subscriber_operation.activate(request)
    try:
        future.result(TIMEOUT)
        logging.info('Successfully subscribed to topic: {}'.format(subscribe_topic))
    except concurrent.futures.TimeoutError as e:
        logging.error('Timeout occurred while subscribing to topic: {}'.format(subscribe_topic), exc_info=True)
        raise e
    except UnauthorizedError as e:
        logging.error('Unauthorized error while subscribing to topic: {}'.format(subscribe_topic), exc_info=True)
        raise e
    except Exception as e:
        logging.error('Exception while subscribing to topic: {}'.format(subscribe_topic), exc_info=True)
        subscriber_operation.close()
        raise e

    # Next, send a publish request to the InfluxDB token request topic
    ipc_publisher_client = awsiot.greengrasscoreipc.connect()
    retries = 0
    try:
        # Retrieve the InfluxDB parameters to connect
        # Retry 10 times or until we retrieve parameters with RW access
        while not handler.influxdb_parameters and retries < 10:
            logging.info("Publish attempt {}".format(retries))
            publish_token_request(ipc_publisher_client, publish_topic)
            logging.info('Successfully published token request to topic: {}'.format(publish_topic))
            retries += 1
            logging.info('Waiting for 10 seconds...')
            time.sleep(10)
            if handler.influxdb_parameters:
                # This component should only accept tokens with RW access, and will reject others in case of conflict
                if handler.influxdb_parameters['InfluxDBTokenAccessType'] != "RW":
                    logging.warning("Discarding retrieved token with incorrect access level {}"
                                    .format(handler.influxdb_parameters['InfluxDBTokenAccessType']))
                    handler.influxdb_parameters = {}
    except Exception:
        logging.error("Received error while sending token publish request!", exc_info=True)
    finally:
        # Close the operations for the clients
        subscriber_operation.close()
        logging.info("Closed InfluxDB parameter response subscriber client")
        if not handler.influxdb_parameters:
            logging.error("Failed to retrieve InfluxDB parameters over IPC!")
            exit(1)
        logging.info("Successfully retrieved InfluxDB metadata and token!")

    return handler.influxdb_parameters


def relay_telemetry(influxdb_parameters) -> None:
    """
    Relay Greengrass system telemetry from Greengrass to InfluxDB.

    Parameters
    ----------
       influxdb_paremeters(str): the retrieved parameters needed to connect to InfluxDB

    Returns
    -------
        None
    """

    # Now we can subscribe to Greengrass Local Telemetry and relay it to InfluxDB using our retrieved credentials
    telemetry_subscriber_client = awsiot.greengrasscoreipc.connect()
    handler = streamHandlers.TelemetryStreamHandler(influxdb_parameters)
    telemetry_operation = telemetry_subscriber_client.new_subscribe_to_topic(handler)
    try:
        request = SubscribeToTopicRequest()
        request.topic = telemetry_topic
        future = telemetry_operation.activate(request)
        future.result(TIMEOUT)
        logging.info('Successfully subscribed to topic: {}'.format(telemetry_topic))
        logging.info('Relaying telemetry to InfluxDB...')
    except concurrent.futures.TimeoutError as e:
        logging.error('Timeout occurred while subscribing to topic: {}'.format(telemetry_topic), exc_info=True)
        raise e
    except UnauthorizedError as e:
        logging.error('Unauthorized error while subscribing to topic: {}'.format(telemetry_topic), exc_info=True)
        raise e
    except Exception as e:
        logging.error('Exception while subscribing to topic: {}'.format(telemetry_topic), exc_info=True)
        telemetry_operation.close()
        raise e


if __name__ == "__main__":

    try:
        args = parse_arguments()
        publish_topic = args.publish_topic
        subscribe_topic = args.subscribe_topic
        influxdb_parameters = retrieve_influxdb_params(publish_topic, subscribe_topic)
        relay_telemetry(influxdb_parameters)
        # Keep the main thread alive, or the process will exit.
        while True:
            time.sleep(10)
    except InterruptedError:
        logging.error('Subscribe interrupted.', exc_info=True)
        exit(1)
    except Exception:
        logging.error('Exception occurred when using IPC.', exc_info=True)
        exit(1)
