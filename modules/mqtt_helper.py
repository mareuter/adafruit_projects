# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT

import adafruit_minimqtt.adafruit_minimqtt as MQTT
import os
import socketpool
import time
import wifi


MQTT_CLIENT_API = "sensors/data"
TIME_IN_NS = 1000000000
LOOP_TIMEOUT = 2  # seconds


class Fields:
    def __init__(self, **kwargs):
        """Class constructor."""
        self.values = dict(**kwargs)

    def __str__(self):
        """Convert content to string removing None parameters.

        Returns
        -------
        `str`
            Stringified representation.
        """
        temp = []
        for k, v in self.values.items():
            if v is None:
                continue
            temp.append(f"{k}={v}")
        return ",".join(temp)


def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker: {str(rc)}")


def on_publish(client, userdata, topic, pid):
    print(f"Data published: {topic} to PID {pid}")


def on_disconnect(client, userdata, rc):
    print("Disconnected from MQTT Broker!")


class MqttHelper:
    def __init__(
        self,
        sensor_name: str,
        pool: socketpool.SocketPool,
        connection_timeout: int = 10,
    ) -> None:
        """Class constructor.

        Parameters
        ----------
        sensor_name : `str`
            The identifier for the sensor.
        pool : `socketpool.SocketPool`
            The connection for the MQTT client.
        connection_timeout : `int`, optional
            The timeout for the client connection, by default 10
        """
        self.sensor_name = sensor_name
        self.connection_timeout = connection_timeout
        self.client = MQTT.MQTT(
            broker=os.getenv("MQTT_BROKER"),
            username=os.getenv("MQTT_USER"),
            password=os.getenv("MQTT_PASSWORD"),
            client_id=sensor_name,
            socket_pool=pool,
            is_ssl=False,
        )
        self.timestamp = None

        self.client.on_connect = on_connect
        self.client.on_publish = on_publish
        self.client.on_disconnect = on_disconnect

        print("Connecting to MQTT broker")
        try:
            self.client.connect(keep_alive=self.connection_timeout)

            try:
                self.client.loop(LOOP_TIMEOUT)
            except (ValueError, RuntimeError) as e:
                print("Failed to get data, retrying\n", e)
                wifi.reset()
                self.client.reconnect()

        except MQTT.MMQTTException as e:
            print("Connection failed: \n", e)
            self.client = None

    def mark_time(self) -> None:
        """Set the timestamp."""
        self.timestamp = time.time() * TIME_IN_NS

    def publish(self, measurements_and_tags: str, fields: Fields) -> None:
        """Write the information to MQTT client.

        Parameters
        ----------
        measurements_and_tags : `str`
            The measurement to publish.
        fields : `Fields`
            The values to publish for the measurement.
        """
        measurements_and_tags.append(f"sensor_id={self.sensor_name}")
        timestamp_str = f"{int(self.timestamp)}"
        data = [
            ",".join(measurements_and_tags),
            str(fields),
            timestamp_str,
        ]
        try:
            self.client.publish(MQTT_CLIENT_API, " ".join(data))
        except Exception as e:
            print(f"Problem publishing: {e}")
