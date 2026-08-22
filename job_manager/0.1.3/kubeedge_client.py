import os
import time

from kubernetes import client, config
from kubernetes.client.rest import ApiException


GROUP = "devices.kubeedge.io"
VERSION = "v1beta1"
DEVICE_PLURAL = "devices"
STATUS_PLURAL = "devicestatuses"


class KubeEdgeClient:
    def __init__(self):
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            config.load_incluster_config()
        else:
            config.load_kube_config()
        self.api = client.CustomObjectsApi()

    def device_status(self, namespace, name):
        return self.api.get_namespaced_custom_object(
            GROUP, VERSION, namespace, STATUS_PLURAL, name
        )

    def list_statuses(self, namespace):
        return self.api.list_namespaced_custom_object(
            GROUP, VERSION, namespace, STATUS_PLURAL
        ).get("items", [])

    def set_requested_action(self, namespace, name, value, metadata=None):
        for attempt in range(5):
            device = self.api.get_namespaced_custom_object(
                GROUP, VERSION, namespace, DEVICE_PLURAL, name
            )
            properties = device.get("spec", {}).get("properties", [])
            target = next((item for item in properties if item.get("name") == "requestedAction"), None)
            if target is None:
                raise RuntimeError(f"{name} has no requestedAction property")
            desired = {"value": value}
            if metadata:
                desired["metadata"] = {key: str(val) for key, val in metadata.items()}
            target["desired"] = desired
            try:
                return self.api.replace_namespaced_custom_object(
                    GROUP, VERSION, namespace, DEVICE_PLURAL, name, device
                )
            except ApiException as exc:
                if exc.status != 409 or attempt == 4:
                    raise
                time.sleep(0.2 * (attempt + 1))
