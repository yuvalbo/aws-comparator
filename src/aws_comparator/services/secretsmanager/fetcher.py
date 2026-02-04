"""
AWS Secrets Manager service fetcher.

This module implements fetching of Secrets Manager secret metadata.
SECURITY CRITICAL: This fetcher NEVER calls get_secret_value().
It only fetches metadata using list_secrets() and describe_secret().
"""

from typing import Any

from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.common import AWSResource
from aws_comparator.models.secretsmanager import SecretMetadata
from aws_comparator.services.base import BaseServiceFetcher


@ServiceRegistry.register(
    "secretsmanager",
    description="AWS Secrets Manager (metadata only, values never fetched)",
    resource_types=["secrets"],
)
class SecretsManagerFetcher(BaseServiceFetcher):
    """
    Fetcher for AWS Secrets Manager resources.

    SECURITY CRITICAL: This fetcher retrieves ONLY secret metadata, including:
    - Secret names and ARNs
    - Rotation configuration
    - Encryption settings (KMS key IDs)
    - Tags and descriptions
    - Timestamps (creation, rotation, access)

    This fetcher NEVER retrieves actual secret values. It uses only:
    - list_secrets() for listing secrets
    - describe_secret() for detailed metadata

    It NEVER calls get_secret_value() or get_secret_value_version().
    This is enforced both in code and should be enforced via IAM policies.
    """

    SERVICE_NAME = "secretsmanager"

    def _create_client(self) -> Any:
        """
        Create boto3 Secrets Manager client.

        Returns:
            Configured boto3 Secrets Manager client
        """
        return self.session.client("secretsmanager", region_name=self.region)

    def fetch_resources(self) -> dict[str, list[AWSResource]]:
        """
        Fetch all Secrets Manager resources.

        SECURITY NOTE: Only fetches metadata, never secret values.

        Returns:
            Dictionary mapping resource types to lists of resources
        """
        return {"secrets": self._safe_fetch("secrets", self._fetch_secrets)}

    def get_resource_types(self) -> list[str]:
        """
        Get list of resource types handled by this fetcher.

        Returns:
            List of resource type names
        """
        return ["secrets"]

    def _fetch_secrets(self) -> list[SecretMetadata]:
        """
        Fetch all secrets and their metadata.

        SECURITY CRITICAL: This method ONLY calls list_secrets() and
        describe_secret(). It NEVER calls get_secret_value().

        Returns:
            List of SecretMetadata resources (no secret values)
        """
        secrets: list[SecretMetadata] = []

        try:
            # Use pagination to list all secrets (metadata only)
            results = self._paginate("list_secrets", "SecretList")

            self.logger.info(f"Found {len(results)} secrets")

            for secret_data in results:
                try:
                    secret_name = secret_data["Name"]

                    # SECURITY CHECK: Verify no secret values in response
                    if "SecretString" in secret_data or "SecretBinary" in secret_data:
                        self.logger.error(
                            f"SECURITY VIOLATION: Secret values found in "
                            f"list_secrets response for {secret_name}"
                        )
                        continue

                    # Get detailed metadata (still no secret values)
                    try:
                        if self.client is None:
                            continue
                        detail_response = self.client.describe_secret(
                            SecretId=secret_name
                        )

                        # SECURITY CHECK: Verify no secret values in detailed response
                        if (
                            "SecretString" in detail_response
                            or "SecretBinary" in detail_response
                        ):
                            self.logger.error(
                                f"SECURITY VIOLATION: Secret values found in "
                                f"describe_secret response for {secret_name}"
                            )
                            continue

                        # Merge list and describe data
                        merged_data = {**secret_data, **detail_response}

                    except ClientError as e:
                        error_code = e.response.get("Error", {}).get("Code", "")
                        if error_code in ["AccessDenied", "ResourceNotFoundException"]:
                            self.logger.warning(
                                f"Cannot describe secret {secret_name}: {error_code}"
                            )
                            # Use list_secrets data only
                            merged_data = secret_data
                        else:
                            raise

                    # Get tags
                    tags = {}
                    if "Tags" in merged_data:
                        tags = self._normalize_tags(merged_data["Tags"])

                    # Create SecretMetadata instance (will validate no secret values)
                    secret = SecretMetadata.from_aws_response(merged_data, tags)
                    secrets.append(secret)

                    self.logger.debug(f"Fetched secret metadata: {secret_name}")

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    secret_name = secret_data.get("Name", "unknown")
                    if error_code in ["AccessDenied", "ResourceNotFoundException"]:
                        self.logger.warning(
                            f"Cannot access secret {secret_name}: {error_code}"
                        )
                    else:
                        self.logger.error(
                            f"Error fetching secret {secret_name}: {e}", exc_info=True
                        )

        except Exception as e:
            self.logger.error(f"Failed to list secrets: {e}", exc_info=True)

        # SECURITY AUDIT LOG
        self.logger.info(
            f"Secrets Manager fetch completed: {len(secrets)} secrets fetched "
            "(metadata only, no secret values retrieved)"
        )

        return secrets
