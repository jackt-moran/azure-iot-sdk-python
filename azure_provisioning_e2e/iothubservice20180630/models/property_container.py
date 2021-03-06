# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class PropertyContainer(Model):
    """Represents Twin properties.

    :param desired: Used in conjunction with reported properties to
     synchronize device configuration or condition. Desired properties can only
     be set by the solution back end and can be read by the device app. The
     device app can also be notified in real time of changes on the desired
     properties.
    :type desired: dict[str, object]
    :param reported: Used in conjunction with desired properties to
     synchronize device configuration or condition. Reported properties can
     only be set by the device app and can be read and queried by the solution
     back end.
    :type reported: dict[str, object]
    """

    _attribute_map = {
        "desired": {"key": "desired", "type": "{object}"},
        "reported": {"key": "reported", "type": "{object}"},
    }

    def __init__(self, desired=None, reported=None):
        super(PropertyContainer, self).__init__()
        self.desired = desired
        self.reported = reported
