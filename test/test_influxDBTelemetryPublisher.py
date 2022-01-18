# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import argparse
import sys
import pytest
import json
from unittest.mock import patch

sys.path.append("src/")


def test_parse_valid_args(mocker):
    mock_parse_args = mocker.patch(
        "argparse.ArgumentParser.parse_args", return_value=argparse.Namespace(
            subscribe_topic="test/subscribe",
            publish_topic="test/publish"
            )
    )
    import src.influxDBTelemetryPublisher as publisher

    args = publisher.parse_arguments()
    assert args.subscribe_topic == "test/subscribe"
    assert args.publish_topic == "test/publish"
    assert mock_parse_args.call_count == 1


def test_parse_no_args(mocker):
    import src.influxDBTelemetryPublisher as publisher

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        publisher.parse_arguments()
    assert pytest_wrapped_e.type == SystemExit


@patch('streamHandlers.InfluxDBDataStreamHandler')
def test_retrieve_influxdb_params(InfluxDBDataStreamHandler, mocker):

    testparams = {
        'InfluxDBContainerName': 'greengrass_InfluxDB',
        'InfluxDBOrg': 'greengrass',
        'InfluxDBBucket': 'greengrass-telemetry',
        'InfluxDBPort': '8086',
        'InfluxDBInterface': '127.0.0.1',
        'InfluxDBRWToken': 'vb53ZyYlxJjAeWcDbgPjbNvkvdD95b2hCrt0CoaZyEL5QYBiQfLw3TbgqgDozj74_aZ9pYCwVJM6Vj5quLAfSA==',
        'InfluxDBServerProtocol': 'https',
        'InfluxDBSkipTLSVerify': 'true'
    }
    mocker.patch("awsiot.greengrasscoreipc.connect")
    handler = InfluxDBDataStreamHandler()
    handler.influxdb_parameters = str.encode(json.dumps(testparams))
    import src.influxDBTelemetryPublisher as publisher
    params = publisher.retrieve_influxdb_params("test/topic", "test/topic")
    assert json.loads(params) == testparams


@patch('streamHandlers.InfluxDBDataStreamHandler')
def test_fail_to_retrieve_influxdb_params(InfluxDBDataStreamHandler, mocker):

    mocker.patch("awsiot.greengrasscoreipc.connect")
    handler = InfluxDBDataStreamHandler()
    handler.influxdb_parameters = None
    import src.influxDBTelemetryPublisher as publisher
    mocker.patch("src.influxDBTelemetryPublisher.publish_token_request", side_effect=ValueError("test"))
    with pytest.raises(SystemExit) as e:
        publisher.retrieve_influxdb_params("test/topic", "test/topic")
        assert e.type == SystemExit
        assert e.value.code == 1
