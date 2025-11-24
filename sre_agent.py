"""
Kubernetes SRE AI Agent - Main Agent Module

This module implements the core SRE agent that monitors Kubernetes clusters,
detects failures, and performs automated remediation.
"""

import logging
from typing import Dict, List, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException


class KubernetesSREAgent:
    """
    Main SRE Agent class for Kubernetes cluster management.

    Capabilities:
    - Detect pod failures and crashes
    - Monitor resource utilization
    - Perform automated remediation
    - Generate diagnostic reports
    """

    def __init__(self, kubeconfig_path: Optional[str] = None):
        """
        Initialize the SRE agent.

        Args:
            kubeconfig_path: Path to kubeconfig file. If None, uses in-cluster config or default kubeconfig.
        """
        self.logger = logging.getLogger(__name__)
        self._initialize_kubernetes_client(kubeconfig_path)

    def _initialize_kubernetes_client(self, kubeconfig_path: Optional[str] = None):
        """Initialize Kubernetes client configuration."""
        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                try:
                    # Try in-cluster config first (when running as pod)
                    config.load_incluster_config()
                except config.ConfigException:
                    # Fall back to kubeconfig file
                    config.load_kube_config()

            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.logger.info("Kubernetes client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise

    def detect_pod_failures(self, namespace: str = "default") -> List[Dict]:
        """
        Detect failed or crashing pods in the specified namespace.

        Args:
            namespace: Kubernetes namespace to monitor

        Returns:
            List of dictionaries containing failed pod information
        """
        failed_pods = []

        try:
            pods = self.core_v1.list_namespaced_pod(namespace)

            for pod in pods.items:
                pod_name = pod.metadata.name
                pod_status = pod.status.phase

                # Check for failed status
                if pod_status in ["Failed", "Unknown"]:
                    failed_pods.append(
                        {
                            "name": pod_name,
                            "namespace": namespace,
                            "status": pod_status,
                            "reason": pod.status.reason,
                            "message": pod.status.message,
                        }
                    )

                # Check for CrashLoopBackOff
                if pod.status.container_statuses:
                    for container in pod.status.container_statuses:
                        if container.state.waiting:
                            if container.state.waiting.reason == "CrashLoopBackOff":
                                failed_pods.append(
                                    {
                                        "name": pod_name,
                                        "namespace": namespace,
                                        "status": "CrashLoopBackOff",
                                        "container": container.name,
                                        "reason": container.state.waiting.reason,
                                        "message": container.state.waiting.message,
                                    }
                                )

            self.logger.info(f"Detected {len(failed_pods)} failed pods in namespace {namespace}")
            return failed_pods

        except ApiException as e:
            self.logger.error(f"Error detecting pod failures: {e}")
            raise

    def restart_failed_pod(self, pod_name: str, namespace: str = "default") -> bool:
        """
        Restart a failed pod by deleting it (assuming it's managed by a controller).

        Args:
            pod_name: Name of the pod to restart
            namespace: Kubernetes namespace

        Returns:
            True if pod was successfully deleted, False otherwise
        """
        try:
            self.core_v1.delete_namespaced_pod(name=pod_name, namespace=namespace, body=client.V1DeleteOptions())
            self.logger.info(f"Successfully deleted pod {pod_name} in namespace {namespace}")
            return True
        except ApiException as e:
            self.logger.error(f"Failed to delete pod {pod_name}: {e}")
            return False

    def get_pod_logs(self, pod_name: str, namespace: str = "default", tail_lines: int = 100) -> str:
        """
        Retrieve logs from a pod for diagnostic purposes.

        Args:
            pod_name: Name of the pod
            namespace: Kubernetes namespace
            tail_lines: Number of log lines to retrieve

        Returns:
            Pod logs as string
        """
        try:
            logs = self.core_v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=tail_lines)
            return logs
        except ApiException as e:
            self.logger.error(f"Failed to retrieve logs for pod {pod_name}: {e}")
            return ""

    def check_deployment_health(self, deployment_name: str, namespace: str = "default") -> Dict:
        """
        Check the health of a deployment.

        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace

        Returns:
            Dictionary containing deployment health information
        """
        try:
            deployment = self.apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)

            replicas = deployment.spec.replicas
            ready_replicas = deployment.status.ready_replicas or 0
            available_replicas = deployment.status.available_replicas or 0

            is_healthy = (ready_replicas == replicas) and (available_replicas == replicas)

            return {
                "name": deployment_name,
                "namespace": namespace,
                "desired_replicas": replicas,
                "ready_replicas": ready_replicas,
                "available_replicas": available_replicas,
                "is_healthy": is_healthy,
            }
        except ApiException as e:
            self.logger.error(f"Failed to check deployment {deployment_name}: {e}")
            raise

    def scale_deployment(self, deployment_name: str, replicas: int, namespace: str = "default") -> bool:
        """
        Scale a deployment to the specified number of replicas.

        Args:
            deployment_name: Name of the deployment
            replicas: Desired number of replicas
            namespace: Kubernetes namespace

        Returns:
            True if scaling was successful, False otherwise
        """
        try:
            # Update the deployment
            body = {"spec": {"replicas": replicas}}

            self.apps_v1.patch_namespaced_deployment_scale(name=deployment_name, namespace=namespace, body=body)

            self.logger.info(f"Successfully scaled deployment {deployment_name} to {replicas} replicas")
            return True
        except ApiException as e:
            self.logger.error(f"Failed to scale deployment {deployment_name}: {e}")
            return False


def setup_logging(level: str = "INFO"):
    """Configure logging for the agent."""
    logging.basicConfig(
        level=getattr(logging, level.upper()), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
