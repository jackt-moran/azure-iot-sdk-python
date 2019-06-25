# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import json
import logging
from azure.iot.device.common.pipeline import pipeline_ops_base, PipelineStage, operation_flow
from . import pipeline_ops_iothub
from . import constant

logger = logging.getLogger(__name__)


class UseSkAuthProviderStage(PipelineStage):
    """
    PipelineStage which handles operations on a Shared Key Authentication Provider.

    This stage handles SetAuthProviderOperation operations.  It parses the connection
    string into it's constituant parts and generates a sas token to pass down.  It
    uses SetAuthProviderArgsOperation to pass the connection string args and the ca_cert
    from the Authentication Provider, and it uses SetSasToken to pass down the
    generated sas token.  After passing down the args and the sas token, this stage
    completes the SetAuthProviderOperation operation.

    All other operations are passed down.
    """

    def _run_op(self, op):
        if isinstance(op, pipeline_ops_iothub.SetAuthProviderOperation):

            def pipeline_ops_done(completed_op):
                op.error = completed_op.error
                op.callback(op)

            auth_provider = op.auth_provider
            operation_flow.run_ops_in_serial(
                self,
                pipeline_ops_iothub.SetAuthProviderArgsOperation(
                    device_id=auth_provider.device_id,
                    module_id=getattr(auth_provider, "module_id", None),
                    hostname=auth_provider.hostname,
                    gateway_hostname=getattr(auth_provider, "gateway_hostname", None),
                    ca_cert=getattr(auth_provider, "ca_cert", None),
                ),
                pipeline_ops_base.SetSasTokenOperation(
                    sas_token=auth_provider.get_current_sas_token()
                ),
                callback=pipeline_ops_done,
            )
        else:
            operation_flow.pass_op_to_next_stage(self, op)


class HandleTwinOperationsStage(PipelineStage):
    """
    PipelineStage which handles twin operations. In particular, it converts twin GET and PATCH
    operations into SendIotRequestAndWaitForResponseOperation operations.  This is done at the IoTHub level because
    there is nothing protocol-specific about this code.  The protocol-specific implementation
    for twin requests and responses is handled inside IoTHubMQTTConverterStage, when it converts
    the SendIotRequestOperation to a protocol-specific send operation and when it converts the
    protocol-specific receive event into an IotResponseEvent event.
    """

    def _run_op(self, op):
        def map_twin_error(original_op, twin_op):
            if twin_op.error:
                original_op.error = twin_op.error
            elif twin_op.status_code >= 300:
                # TODO map error codes to correct exceptions
                logger.error("Error {} received from twin operation".format(twin_op.status_code))
                logger.error("response body: {}".format(twin_op.response_body))
                original_op.error = Exception(
                    "twin operation returned status {}".format(twin_op.status_code)
                )

        if isinstance(op, pipeline_ops_iothub.GetTwinOperation):

            def on_twin_response(twin_op):
                logger.info("{}({}): Got response for GetTwinOperation".format(self.name, op.name))
                map_twin_error(original_op=op, twin_op=twin_op)
                if not twin_op.error:
                    op.twin = json.loads(twin_op.response_body.decode("utf-8"))
                operation_flow.complete_op(self, op)

            operation_flow.pass_op_to_next_stage(
                self,
                pipeline_ops_base.SendIotRequestAndWaitForResponseOperation(
                    request_type=constant.TWIN,
                    method="GET",
                    resource_location="/",
                    request_body=" ",
                    callback=on_twin_response,
                ),
            )

        elif isinstance(op, pipeline_ops_iothub.PatchTwinReportedPropertiesOperation):

            def on_twin_response(twin_op):
                logger.info(
                    "{}({}): Got response for PatchTwinReportedPropertiesOperation operation".format(
                        self.name, op.name
                    )
                )
                map_twin_error(original_op=op, twin_op=twin_op)
                operation_flow.complete_op(self, op)

            logger.info(
                "{}({}): Sending reported properties patch: {}".format(self.name, op.name, op.patch)
            )

            operation_flow.pass_op_to_next_stage(
                self,
                (
                    pipeline_ops_base.SendIotRequestAndWaitForResponseOperation(
                        request_type=constant.TWIN,
                        method="PATCH",
                        resource_location="/properties/reported/",
                        request_body=json.dumps(op.patch),
                        callback=on_twin_response,
                    )
                ),
            )

        else:
            operation_flow.pass_op_to_next_stage(self, op)