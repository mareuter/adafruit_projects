# SPDX-FileCopyrightText: 2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

from adafruit_io.adafruit_io import IO_MQTT
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io_errors import AdafruitIO_MQTTError
import os
import socketpool
import wifi

__all__ = ["AioHelper"]

LOOP_TIMEOUT = 2  # seconds


def connected(client):
    # Connected function will be called when the client is connected to Adafruit IO.
    # This is a good place to subscribe to feed changes.  The client parameter
    # passed to this function is the Adafruit IO MQTT client so you can make
    # calls against it easily.
    print("Connected to Adafruit IO!  Listening for changes...")


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))


def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))


def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")


def publish(client, userdata, topic, pid):
    # This method is called when the client publishes data to a feed.
    print("Published to {0} with PID {1}".format(topic, pid))
    if userdata is not None:
        print("Published User data: ", end="")
        print(userdata)


class AioHelper:
    def __init__(
        self,
        pool: socketpool.SocketPool,
    ) -> None:
        """Class constructor.

        Parameters
        ----------
        pool : socketpool.SocketPool
            The connection for the MQTT client.
        """
        temp_client = MQTT.MQTT(
            broker="io.adafruit.com",
            port=1883,
            username=os.getenv("ADAFRUIT_AIO_USERNAME"),
            password=os.getenv("ADAFRUIT_AIO_KEY"),
            socket_pool=pool,
            is_ssl=True,
        )

        self.client = IO_MQTT(temp_client)

        self.client.on_connect = connected
        self.client.on_disconnect = disconnected
        self.client.on_subscribe = subscribe
        self.client.on_unsubscribe = unsubscribe
        self.client.on_publish = publish

        print("Connecting to Adafruit IO")
        try:
            self.client.connect()
            try:
                self.client.loop(LOOP_TIMEOUT)
            except (ValueError, RuntimeError) as e:
                print("Failed to get data, retrying\n", e)
                wifi.reset()
                self.client.reconnect()

        except AdafruitIO_MQTTError as e:
            print("Connection failed: \n", e)
            self.client = None

    def publish(self, feed_name: str, value: int | float | str) -> None:
        """Publish a value to the given feed.

        Parameters
        ----------
        feed_name : str
            Feed name
        value : int | float | str
            Value to publish to feed
        """
        try:
            self.client.publish(feed_name, value)
        except Exception as e:
            print(f"Problem publishing: {e}")

    def publish_multi(
        self, feeds_and_data: list[tuple[str, int | float | str]]
    ) -> None:
        """Publish multiple values for feeds."""
        try:
            self.client.publish_multiple(feeds_and_data=feeds_and_data)
        except Exception as e:
            print(f"Problem publishing: {e}")
