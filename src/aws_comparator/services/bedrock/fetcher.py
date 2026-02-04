"""
AWS Bedrock service fetcher.

This module implements fetching of Bedrock model resources and configurations.
"""

from typing import Any

from botocore.exceptions import ClientError

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.bedrock import (
    CustomModel,
    FoundationModel,
    Guardrail,
    ProvisionedModelThroughput,
)
from aws_comparator.models.common import AWSResource
from aws_comparator.services.base import BaseServiceFetcher


@ServiceRegistry.register(
    "bedrock",
    description="Amazon Bedrock (Foundation Models)",
    resource_types=[
        "foundation_models",
        "custom_models",
        "provisioned_throughput",
        "guardrails",
    ],
)
class BedrockFetcher(BaseServiceFetcher):
    """
    Fetcher for AWS Bedrock resources.

    This fetcher retrieves Bedrock information including:
    - Foundation models (available models from providers)
    - Custom models (fine-tuned models)
    - Provisioned model throughput configurations
    - Guardrails for content filtering

    Note: Bedrock service availability varies by region. This fetcher
    handles cases where the service is not available gracefully.
    """

    SERVICE_NAME = "bedrock"

    def _create_client(self) -> Any:
        """
        Create boto3 Bedrock client.

        Returns:
            Configured boto3 Bedrock client
        """
        return self.session.client("bedrock", region_name=self.region)

    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all Bedrock resources.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {
            "foundation_models": self._safe_fetch(
                "foundation_models", self._fetch_foundation_models
            ),
            "custom_models": self._safe_fetch(
                "custom_models", self._fetch_custom_models
            ),
            "provisioned_throughput": self._safe_fetch(
                "provisioned_throughput", self._fetch_provisioned_throughput
            ),
            "guardrails": self._safe_fetch("guardrails", self._fetch_guardrails),
        }

    def get_resource_types(self) -> list[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return [
            "foundation_models",
            "custom_models",
            "provisioned_throughput",
            "guardrails",
        ]

    def _fetch_foundation_models(self) -> list[FoundationModel]:
        """
        Fetch all available foundation models.

        Returns:
            List of FoundationModel resources
        """
        models: list[FoundationModel] = []

        try:
            # List foundation models (no pagination needed for this API)
            response = self.client.list_foundation_models()
            model_summaries = response.get("modelSummaries", [])

            self.logger.info(f"Found {len(model_summaries)} Bedrock foundation models")

            for model_data in model_summaries:
                try:
                    model = FoundationModel.from_aws_response(model_data)
                    models.append(model)

                    self.logger.debug(f"Fetched foundation model: {model.model_id}")

                except Exception as e:
                    model_id = model_data.get("modelId", "unknown")
                    self.logger.error(
                        f"Error processing foundation model {model_id}: {e}",
                        exc_info=True,
                    )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["AccessDenied", "UnauthorizedOperation"]:
                self.logger.warning(
                    f"Cannot access Bedrock foundation models: {error_code}"
                )
            else:
                self.logger.error(
                    f"Error fetching foundation models: {e}", exc_info=True
                )

        except Exception as e:
            self.logger.error(f"Failed to list foundation models: {e}", exc_info=True)

        return models

    def _fetch_custom_models(self) -> list[CustomModel]:
        """
        Fetch all custom fine-tuned models.

        Returns:
            List of CustomModel resources
        """
        models: list[CustomModel] = []

        try:
            # Use pagination for custom models
            paginator = self.client.get_paginator("list_custom_models")
            page_iterator = paginator.paginate()

            for page in page_iterator:
                model_summaries = page.get("modelSummaries", [])

                for model_data in model_summaries:
                    try:
                        model = CustomModel.from_aws_response(model_data)
                        models.append(model)

                        self.logger.debug(f"Fetched custom model: {model.model_name}")

                    except Exception as e:
                        model_name = model_data.get("modelName", "unknown")
                        self.logger.error(
                            f"Error processing custom model {model_name}: {e}",
                            exc_info=True,
                        )

            self.logger.info(f"Found {len(models)} Bedrock custom models")

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["AccessDenied", "UnauthorizedOperation"]:
                self.logger.warning(
                    f"Cannot access Bedrock custom models: {error_code}"
                )
            else:
                self.logger.error(f"Error fetching custom models: {e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Failed to list custom models: {e}", exc_info=True)

        return models

    def _fetch_provisioned_throughput(self) -> list[ProvisionedModelThroughput]:
        """
        Fetch all provisioned model throughput configurations.

        Returns:
            List of ProvisionedModelThroughput resources
        """
        throughputs: list[ProvisionedModelThroughput] = []

        try:
            # Use pagination for provisioned throughput
            paginator = self.client.get_paginator("list_provisioned_model_throughputs")
            page_iterator = paginator.paginate()

            for page in page_iterator:
                throughput_summaries = page.get("provisionedModelSummaries", [])

                for throughput_data in throughput_summaries:
                    try:
                        throughput = ProvisionedModelThroughput.from_aws_response(
                            throughput_data
                        )
                        throughputs.append(throughput)

                        self.logger.debug(
                            f"Fetched provisioned throughput: {throughput.provisioned_model_name}"
                        )

                    except Exception as e:
                        name = throughput_data.get("provisionedModelName", "unknown")
                        self.logger.error(
                            f"Error processing provisioned throughput {name}: {e}",
                            exc_info=True,
                        )

            self.logger.info(
                f"Found {len(throughputs)} Bedrock provisioned throughputs"
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["AccessDenied", "UnauthorizedOperation"]:
                self.logger.warning(
                    f"Cannot access Bedrock provisioned throughput: {error_code}"
                )
            else:
                self.logger.error(
                    f"Error fetching provisioned throughput: {e}", exc_info=True
                )

        except Exception as e:
            self.logger.error(
                f"Failed to list provisioned throughput: {e}", exc_info=True
            )

        return throughputs

    def _fetch_guardrails(self) -> list[Guardrail]:
        """
        Fetch all guardrails.

        Returns:
            List of Guardrail resources
        """
        guardrails: list[Guardrail] = []

        try:
            # Use pagination for guardrails
            paginator = self.client.get_paginator("list_guardrails")
            page_iterator = paginator.paginate()

            for page in page_iterator:
                guardrail_summaries = page.get("guardrails", [])

                for guardrail_data in guardrail_summaries:
                    try:
                        guardrail = Guardrail.from_aws_response(guardrail_data)
                        guardrails.append(guardrail)

                        self.logger.debug(f"Fetched guardrail: {guardrail.name}")

                    except Exception as e:
                        name = guardrail_data.get("name", "unknown")
                        self.logger.error(
                            f"Error processing guardrail {name}: {e}", exc_info=True
                        )

            self.logger.info(f"Found {len(guardrails)} Bedrock guardrails")

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["AccessDenied", "UnauthorizedOperation"]:
                self.logger.warning(f"Cannot access Bedrock guardrails: {error_code}")
            else:
                self.logger.error(f"Error fetching guardrails: {e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Failed to list guardrails: {e}", exc_info=True)

        return guardrails
