"""
Orchestration engine for coordinating comparison operations.

This module contains the ComparisonOrchestrator that coordinates
service fetching, comparison, and reporting across multiple services.
"""

import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

import aws_comparator.services.bedrock  # noqa: F401
import aws_comparator.services.cloudwatch  # noqa: F401
import aws_comparator.services.ec2  # noqa: F401
import aws_comparator.services.elasticbeanstalk  # noqa: F401
import aws_comparator.services.eventbridge  # noqa: F401
import aws_comparator.services.lambda_service  # noqa: F401
import aws_comparator.services.pinpoint  # noqa: F401
import aws_comparator.services.s3  # noqa: F401
import aws_comparator.services.secretsmanager  # noqa: F401
import aws_comparator.services.servicequotas  # noqa: F401
import aws_comparator.services.sqs  # noqa: F401
from aws_comparator.comparison import (
    BedrockComparator,
    CloudWatchComparator,
    EC2Comparator,
    ElasticBeanstalkComparator,
    EventBridgeComparator,
    LambdaComparator,
    ResourceComparator,
    S3Comparator,
    SecretsManagerComparator,
    ServiceQuotasComparator,
    SQSComparator,
)
from aws_comparator.core.config import AccountConfig, ComparisonConfig
from aws_comparator.core.exceptions import (
    AssumeRoleError,
    CredentialsNotFoundError,
    InvalidCredentialsError,
    ServiceNotSupportedError,
)
from aws_comparator.core.registry import ServiceRegistry
from aws_comparator.models.comparison import (
    ChangeSeverity,
    ComparisonReport,
    ReportSummary,
    ServiceComparisonResult,
    ServiceError,
)

logger = logging.getLogger(__name__)


# Type alias for progress callback
ProgressCallback = Callable[[str, int, int], None]


class ComparisonOrchestrator:
    """
    Central coordinator for account comparison operations.

    This class orchestrates:
    1. Authentication with both AWS accounts
    2. Discovery and filtering of services
    3. Parallel execution of service fetchers
    4. Aggregation of comparison results
    5. Generation of final reports

    Attributes:
        config: Configuration for the comparison operation.
        progress_callback: Optional callback for progress updates.
    """

    def __init__(
        self,
        config: ComparisonConfig,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        """
        Initialize the orchestrator.

        Args:
            config: Configuration for the comparison operation.
            progress_callback: Optional callback for progress updates.
                Signature: callback(service_name: str, current: int, total: int)
        """
        self.config = config
        self.progress_callback = progress_callback
        self.logger = logging.getLogger(__name__)
        self._session1: Optional[boto3.Session] = None
        self._session2: Optional[boto3.Session] = None

    def _create_session(self, account_config: AccountConfig) -> boto3.Session:
        """
        Create a boto3 session for an AWS account.

        This method handles both profile-based and role-based authentication.

        Args:
            account_config: Configuration for the AWS account.

        Returns:
            Configured boto3 Session.

        Raises:
            CredentialsNotFoundError: If credentials cannot be found.
            InvalidCredentialsError: If credentials are invalid.
            AssumeRoleError: If role assumption fails.
        """
        try:
            # Create base session
            if account_config.profile:
                self.logger.debug(f"Creating session with profile: {account_config.profile}")
                session = boto3.Session(
                    profile_name=account_config.profile,
                    region_name=account_config.region,
                )
            else:
                self.logger.debug("Creating session with default credentials")
                session = boto3.Session(region_name=account_config.region)

            # If role ARN is specified, assume the role
            if account_config.role_arn:
                session = self._assume_role(session, account_config)

            # Validate the session by making a simple API call
            self._validate_session(session, account_config.account_id)

            return session

        except ProfileNotFound as e:
            raise InvalidCredentialsError(
                f"Profile not found: {account_config.profile}"
            ) from e
        except NoCredentialsError as e:
            raise CredentialsNotFoundError() from e
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["InvalidClientTokenId", "SignatureDoesNotMatch"]:
                raise InvalidCredentialsError(str(e)) from e
            raise

    def _assume_role(
        self, session: boto3.Session, account_config: AccountConfig
    ) -> boto3.Session:
        """
        Assume an IAM role and return a new session with temporary credentials.

        Args:
            session: Base boto3 session to use for assuming the role.
            account_config: Account configuration containing role ARN.

        Returns:
            New boto3 Session with assumed role credentials.

        Raises:
            AssumeRoleError: If role assumption fails.
        """
        self.logger.debug(f"Assuming role: {account_config.role_arn}")

        try:
            sts_client = session.client("sts")

            assume_role_params: dict[str, Any] = {
                "RoleArn": account_config.role_arn,
                "RoleSessionName": account_config.session_name or "aws-comparator-session",
            }

            if account_config.external_id:
                assume_role_params["ExternalId"] = account_config.external_id

            response = sts_client.assume_role(**assume_role_params)
            credentials = response["Credentials"]

            return boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=account_config.region,
            )

        except ClientError as e:
            error_message = e.response.get("Error", {}).get("Message", str(e))
            raise AssumeRoleError(account_config.role_arn or "", error_message) from e

    def _validate_session(self, session: boto3.Session, expected_account_id: str) -> None:
        """
        Validate that the session has valid credentials and matches expected account.

        Args:
            session: boto3 Session to validate.
            expected_account_id: Expected AWS account ID.

        Raises:
            InvalidCredentialsError: If credentials are invalid or account doesn't match.
        """
        try:
            sts_client = session.client("sts")
            identity = sts_client.get_caller_identity()
            actual_account_id = identity.get("Account")

            if actual_account_id != expected_account_id:
                self.logger.warning(
                    f"Account ID mismatch: expected {expected_account_id}, "
                    f"got {actual_account_id}"
                )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ["InvalidClientTokenId", "SignatureDoesNotMatch", "AccessDenied"]:
                raise InvalidCredentialsError(str(e)) from e
            raise

    def _get_services_to_compare(self) -> list[str]:
        """
        Get the list of services to compare based on configuration.

        Returns:
            List of service names to compare.

        Raises:
            ServiceNotSupportedError: If any specified service is not supported.
        """
        available_services = ServiceRegistry.list_services()

        if self.config.services:
            # Validate requested services
            valid_services, invalid_services = ServiceRegistry.validate_services(
                self.config.services
            )

            if invalid_services:
                self.logger.warning(
                    f"Invalid services ignored: {invalid_services}. "
                    f"Available services: {available_services}"
                )

            if not valid_services:
                raise ServiceNotSupportedError(
                    f"None of the specified services are supported: {self.config.services}"
                )

            return valid_services

        return available_services

    def _fetch_service_data(
        self,
        service_name: str,
        session: boto3.Session,
        region: str,
    ) -> tuple[str, dict[str, list[Any]], Optional[str]]:
        """
        Fetch resources for a single service from one account.

        Args:
            service_name: Name of the service to fetch.
            session: boto3 Session for the account.
            region: AWS region to fetch from.

        Returns:
            Tuple of (service_name, resources_dict, error_message or None).
        """
        try:
            fetcher = ServiceRegistry.get_fetcher(service_name, session, region)
            resources = fetcher.fetch_resources()
            return (service_name, resources, None)
        except Exception as e:
            error_msg = f"Failed to fetch {service_name}: {e}"
            self.logger.error(error_msg, exc_info=True)
            return (service_name, {}, error_msg)

    def _compare_service(
        self,
        service_name: str,
        account1_data: dict[str, list[Any]],
        account2_data: dict[str, list[Any]],
    ) -> ServiceComparisonResult:
        """
        Compare resources from a single service between two accounts.

        Uses service-specific comparators when available (e.g., ServiceQuotasComparator
        for service-quotas), otherwise falls back to the generic ResourceComparator.

        Args:
            service_name: Name of the service.
            account1_data: Resources from first account.
            account2_data: Resources from second account.

        Returns:
            ServiceComparisonResult for the service.
        """
        # Map service names to their specialized comparators
        # These comparators use name-based matching instead of ARN-based matching
        # which is essential for cross-account comparison
        comparator_map = {
            'service-quotas': ServiceQuotasComparator,
            'cloudwatch': CloudWatchComparator,
            'eventbridge': EventBridgeComparator,
            'secretsmanager': SecretsManagerComparator,
            'lambda': LambdaComparator,
            's3': S3Comparator,
            'ec2': EC2Comparator,
            'sqs': SQSComparator,
            'bedrock': BedrockComparator,
            'elasticbeanstalk': ElasticBeanstalkComparator,
        }

        # Use service-specific comparator if available, otherwise use generic
        comparator_class = comparator_map.get(service_name, ResourceComparator)
        comparator = comparator_class(service_name)
        return comparator.compare(account1_data, account2_data)

    def _calculate_summary(
        self,
        results: list[ServiceComparisonResult],
        errors: list[ServiceError],
        execution_time: float,
    ) -> ReportSummary:
        """
        Calculate summary statistics from comparison results.

        Args:
            results: List of service comparison results.
            errors: List of errors encountered.
            execution_time: Total execution time in seconds.

        Returns:
            ReportSummary with aggregated statistics.
        """
        total_changes = 0
        total_resources_account1 = 0
        total_resources_account2 = 0
        services_with_changes = 0
        changes_by_severity: dict[str, int] = {
            severity.value: 0 for severity in ChangeSeverity
        }

        for result in results:
            total_changes += result.total_changes
            if result.total_changes > 0:
                services_with_changes += 1

            for resource_comp in result.resource_comparisons.values():
                total_resources_account1 += resource_comp.account1_count
                total_resources_account2 += resource_comp.account2_count

                # Count changes by severity
                for change_list in [
                    resource_comp.added,
                    resource_comp.removed,
                    resource_comp.modified,
                ]:
                    for change in change_list:
                        severity_key = change.severity.value
                        changes_by_severity[severity_key] = (
                            changes_by_severity.get(severity_key, 0) + 1
                        )

        return ReportSummary(
            total_services_compared=len(results),
            total_services_with_changes=services_with_changes,
            total_changes=total_changes,
            total_resources_account1=total_resources_account1,
            total_resources_account2=total_resources_account2,
            changes_by_severity=changes_by_severity,
            services_with_errors=[e.service_name for e in errors],
            execution_time_seconds=execution_time,
        )

    def compare_accounts(self) -> ComparisonReport:
        """
        Execute the complete account comparison workflow.

        This method:
        1. Creates boto3 sessions for both accounts
        2. Discovers available services
        3. Fetches resources in parallel from both accounts
        4. Compares resources for each service
        5. Aggregates results into a ComparisonReport

        Returns:
            ComparisonReport with all comparison results.

        Raises:
            AuthenticationError: If authentication fails for either account.
        """
        start_time = time.time()
        self.logger.info("Starting account comparison")
        self.logger.info(f"Account 1: {self.config.account1.account_id}")
        self.logger.info(f"Account 2: {self.config.account2.account_id}")

        # Create sessions for both accounts
        self.logger.info("Authenticating with AWS accounts...")
        self._session1 = self._create_session(self.config.account1)
        self._session2 = self._create_session(self.config.account2)

        # Get services to compare
        services_to_compare = self._get_services_to_compare()
        self.logger.info(f"Services to compare: {services_to_compare}")

        # Fetch resources and compare
        results: list[ServiceComparisonResult] = []
        errors: list[ServiceError] = []
        services_compared: list[str] = []

        total_services = len(services_to_compare)
        region = self.config.account1.region

        if self.config.parallel_execution:
            # Parallel execution
            results, errors, services_compared = self._compare_services_parallel(
                services_to_compare, region, total_services
            )
        else:
            # Sequential execution
            results, errors, services_compared = self._compare_services_sequential(
                services_to_compare, region, total_services
            )

        execution_time = time.time() - start_time

        # Calculate summary
        summary = self._calculate_summary(results, errors, execution_time)

        self.logger.info(
            f"Comparison complete. {summary.total_changes} changes found "
            f"across {summary.total_services_with_changes}/{summary.total_services_compared} "
            f"services in {execution_time:.2f}s"
        )

        return ComparisonReport(
            account1_id=self.config.account1.account_id,
            account2_id=self.config.account2.account_id,
            region=region,
            services_compared=services_compared,
            timestamp=datetime.utcnow(),
            results=results,
            summary=summary,
            errors=errors,
        )

    def _compare_services_parallel(
        self,
        services: list[str],
        region: str,
        total_services: int,
    ) -> tuple[list[ServiceComparisonResult], list[ServiceError], list[str]]:
        """
        Compare services in parallel using ThreadPoolExecutor.

        Args:
            services: List of services to compare.
            region: AWS region.
            total_services: Total number of services for progress reporting.

        Returns:
            Tuple of (results, errors, services_compared).
        """
        results: list[ServiceComparisonResult] = []
        errors: list[ServiceError] = []
        services_compared: list[str] = []

        max_workers = min(self.config.max_workers, len(services) * 2)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit fetch tasks for both accounts in parallel
            fetch_futures = {}

            for service_name in services:
                # Submit fetch for account 1
                future1 = executor.submit(
                    self._fetch_service_data,
                    service_name,
                    self._session1,
                    region,
                )
                fetch_futures[(service_name, 1)] = future1

                # Submit fetch for account 2
                future2 = executor.submit(
                    self._fetch_service_data,
                    service_name,
                    self._session2,
                    region,
                )
                fetch_futures[(service_name, 2)] = future2

            # Collect fetch results
            account1_data: dict[str, dict[str, list[Any]]] = {}
            account2_data: dict[str, dict[str, list[Any]]] = {}
            fetch_errors: dict[str, list[str]] = {}

            for (service_name, account_num), future in fetch_futures.items():
                try:
                    _, resources, error = future.result()
                    if account_num == 1:
                        account1_data[service_name] = resources
                    else:
                        account2_data[service_name] = resources

                    if error:
                        if service_name not in fetch_errors:
                            fetch_errors[service_name] = []
                        fetch_errors[service_name].append(
                            f"Account {account_num}: {error}"
                        )
                except Exception as exc:
                    if service_name not in fetch_errors:
                        fetch_errors[service_name] = []
                    fetch_errors[service_name].append(
                        f"Account {account_num}: {str(exc)}"
                    )

            # Compare services
            for idx, service_name in enumerate(services, 1):
                if self.progress_callback:
                    self.progress_callback(service_name, idx, total_services)

                try:
                    data1 = account1_data.get(service_name, {})
                    data2 = account2_data.get(service_name, {})

                    result = self._compare_service(service_name, data1, data2)

                    # Add any fetch errors to the result
                    if service_name in fetch_errors:
                        result.errors.extend(fetch_errors[service_name])

                    results.append(result)
                    services_compared.append(service_name)

                except Exception as exc:
                    self.logger.error(
                        f"Error comparing service {service_name}: {exc}",
                        exc_info=True,
                    )
                    errors.append(
                        ServiceError(
                            service_name=service_name,
                            error_type=type(exc).__name__,
                            error_message=str(exc),
                            traceback=traceback.format_exc(),
                        )
                    )

        return results, errors, services_compared

    def _compare_services_sequential(
        self,
        services: list[str],
        region: str,
        total_services: int,
    ) -> tuple[list[ServiceComparisonResult], list[ServiceError], list[str]]:
        """
        Compare services sequentially.

        Args:
            services: List of services to compare.
            region: AWS region.
            total_services: Total number of services for progress reporting.

        Returns:
            Tuple of (results, errors, services_compared).
        """
        results: list[ServiceComparisonResult] = []
        errors: list[ServiceError] = []
        services_compared: list[str] = []

        for idx, service_name in enumerate(services, 1):
            if self.progress_callback:
                self.progress_callback(service_name, idx, total_services)

            try:
                self.logger.info(f"Processing service: {service_name}")

                # Fetch from both accounts
                _, data1, error1 = self._fetch_service_data(
                    service_name, self._session1, region
                )
                _, data2, error2 = self._fetch_service_data(
                    service_name, self._session2, region
                )

                # Compare
                result = self._compare_service(service_name, data1, data2)

                # Add fetch errors if any
                if error1:
                    result.errors.append(f"Account 1: {error1}")
                if error2:
                    result.errors.append(f"Account 2: {error2}")

                results.append(result)
                services_compared.append(service_name)

            except Exception as exc:
                self.logger.error(
                    f"Error processing service {service_name}: {exc}",
                    exc_info=True,
                )
                errors.append(
                    ServiceError(
                        service_name=service_name,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                        traceback=traceback.format_exc(),
                    )
                )

        return results, errors, services_compared
