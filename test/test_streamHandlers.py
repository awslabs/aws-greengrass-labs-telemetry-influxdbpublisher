# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import sys
import pytest
import json
from unittest.mock import patch, ANY
import src.streamHandlers as streamHandler

from awsiot.greengrasscoreipc.model import (
    JsonMessage,
    BinaryMessage,
    SubscriptionResponseMessage
)

sys.path.append("src/")

testparams = {
    'InfluxDBContainerName': 'greengrass_InfluxDB',
    'InfluxDBOrg': 'greengrass',
    'InfluxDBBucket': 'greengrass-telemetry',
    'InfluxDBPort': '8086',
    'InfluxDBInterface': '127.0.0.1',
    'InfluxDBToken': 'vb53ZyYlxJjAeWcDbgPjbNvkvdD95b2hCrt0CoaZyEL5QYBiQfLw3TbgqgDozj74_aZ9pYCwVJM6Vj5quLAfSA==',
    'InfluxDBServerProtocol': 'https',
    'InfluxDBSkipTLSVerify': 'true',
    'InfluxDBTokenAccessType': 'RW'
}


def test_validInfluxDBParams(mocker):

    handler = streamHandler.InfluxDBDataStreamHandler()
    message = JsonMessage(message=testparams)
    response_message = SubscriptionResponseMessage(json_message=message)
    handler.on_stream_event(response_message)
    assert handler.influxdb_parameters == testparams


def test_invalidInfluxDBParams(mocker):
    import src.streamHandlers as streamHandler

    emptyparams = {}

    handler = streamHandler.InfluxDBDataStreamHandler()
    message = JsonMessage(message=emptyparams)
    response_message = SubscriptionResponseMessage(json_message=message)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        handler.on_stream_event(response_message)
        assert pytest_wrapped_e.type == SystemExit


@patch('influxdb_client.InfluxDBClient')
def test_valid_telemetry_received(InfluxDBClient, mocker):

    client = InfluxDBClient("http://localhost", "my-token", org="my-org", debug=True)

    testTelemetry = [
        {"A": "Average", "N": "CpuUsage", "NS": "SystemMetrics", "TS": 1627597331445, "U": "Percent", "V": 26.21981271562346},
        {"A": "Count", "N": "TotalNumberOfFDs", "NS": "SystemMetrics", "TS": 1627597331445, "U": "Count", "V": 7316},
        {"A": "Count", "N": "SystemMemUsage", "NS": "SystemMetrics", "TS": 1627597331445, "U": "Megabytes", "V": 10098}
    ]

    handler = streamHandler.TelemetryStreamHandler(testparams)
    binary_message = BinaryMessage(message=str.encode(json.dumps(testTelemetry)))
    response_message = SubscriptionResponseMessage(binary_message=binary_message)
    handler.on_stream_event(response_message)

    assert client.write_api.called
    handler.write_client.write.assert_called_with(
        bucket=testparams['InfluxDBBucket'], org=testparams['InfluxDBOrg'], record=ANY)


def test_none_telemetry_received():
    handler = streamHandler.TelemetryStreamHandler(testparams)
    response_message = None
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        handler.on_stream_event(response_message)
        assert pytest_wrapped_e.type == SystemExit


def test_empty_telemetry_received():
    emptyEvent = ""
    handler = streamHandler.TelemetryStreamHandler(testparams)
    binary_message = BinaryMessage(message=str.encode(json.dumps(emptyEvent)))
    response_message = SubscriptionResponseMessage(binary_message=binary_message)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        handler.on_stream_event(response_message)
        assert pytest_wrapped_e.type == SystemExit
