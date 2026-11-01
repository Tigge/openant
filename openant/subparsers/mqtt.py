import argparse
import json
import uuid

import paho.mqtt.client as mqtt

from ..base.datatarget import DataTarget
from ..devices.common import AntPlusDevice, DeviceData


class MqttTarget(DataTarget):

    def __init__(self, args: argparse.Namespace):
        super().__init__(args)
        self.args = args
        self.client_id: str = "openant-mqtt_" + str(uuid.uuid4())
        self.mqttc: mqtt.Client = self._create_client(args)
        self.device_topics: dict[tuple[int, int], str] = dict(
            self.args.device_topics or []
        )

    def write_data(
        self, device: AntPlusDevice, page_name: str, data: DeviceData
    ) -> None:
        super().write_data(device, page_name, data)
        device_topic = self._determine_topic(device)
        x = data.to_influx_json({})
        payload = {"_type": x["measurement"]}
        payload.update(x["fields"])

        if self.args.topic_per_field:
            for field, value in payload.items():
                field_topic = device_topic + "/" + field
                self.mqttc.publish(field_topic, value)
        else:
            payload = json.dumps(payload)
            self.mqttc.publish(device_topic, payload)

    def close(self) -> None:
        super().close()
        self.mqttc.disconnect()
        self.mqttc.loop_stop()

    def _create_client(self, args: argparse.Namespace) -> mqtt.Client:
        mqttc = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=self.client_id,
            clean_session=False,
            userdata=self,
        )
        mqttc.username_pw_set(args.user, args.password)
        mqttc.reconnect_delay_set(min_delay=5, max_delay=120)
        mqttc.on_connect = self.on_connect
        mqttc.on_disconnect = self.on_disconnect
        mqttc.connect(args.host, args.port)
        mqttc.loop_start()
        return mqttc

    def _determine_topic(self, device: AntPlusDevice) -> str:
        topic = f"openant/{type(device).__name__}/{device.device_id}"
        key = device.device_type, device.device_id
        return self.device_topics.get(key, topic)

    @staticmethod
    def on_connect(
        client: mqtt.Client, userdata, connect_flags, reason_code, properties
    ):
        print(f"Connected to MQTT server: {reason_code}")

    @staticmethod
    def on_disconnect(
        client: mqtt.Client, userdata, disconnect_flags, reason_code, properties
    ):
        target: DataTarget = userdata
        if target.shutting_down:
            print("Disconnected from MQTT server (shutting down)")
        else:
            print(f"Disconnected from MQTT server ({reason_code}), will reconnect")


def add_subparser(subparsers, name="mqtt"):
    antmqtt = subparsers.add_parser(
        name,
        description=(
            "Capture DeviceData from an ANT+ device and publish to MQTT server."
            "Data will be published under openant/<DeviceType>/<DeviceId> by default."
            "If you wish to control the topic in detail, use --device-topic."
        ),
    )
    DataTarget.add_general_arguments(antmqtt)
    mqtt_args = antmqtt.add_argument_group(f"{name} options")
    mqtt_args.add_argument(
        "--host",
        default="localhost",
        type=str,
        help="Host for MQTT server",
    )
    mqtt_args.add_argument(
        "--port",
        default=1883,
        type=int,
        help="Port for MQTT server",
    )
    mqtt_args.add_argument(
        "--user",
        type=str,
        help="User for MQTT server",
    )
    mqtt_args.add_argument(
        "--password",
        type=str,
        help="Password for MQTT server",
    )
    mqtt_args.add_argument(
        "--topic-per-field",
        action="store_true",
        help="Publish fields to individual topics under the device node, rather than all fields as JSON)",
    )

    def device_topic(s):
        try:
            temp = s.split(":", 3)
            return tuple(map(int, temp[0:2])), temp[2]
        except Exception as exc:
            raise argparse.ArgumentTypeError(
                f"Invalid value: {s}. Format must be type:id:topic. E.g. "
                "120:54368:fixed/topic/name"
            ) from exc

    mqtt_args.add_argument(
        "--device-topic",
        action="append",
        type=device_topic,
        dest="device_topics",
        help="Specify which topic to post device data to. On the form type:id:topic. May be repeated.",
    )
    antmqtt.set_defaults(func=MqttTarget.entry)
