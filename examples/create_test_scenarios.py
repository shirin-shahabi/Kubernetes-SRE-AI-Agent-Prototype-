"""
Example: Create problematic pods for testing the SRE agent
"""
import yaml
from pathlib import Path

# Create examples directory
examples_dir = Path("examples/k8s")
examples_dir.mkdir(parents=True, exist_ok=True)

# 1. CrashLoopBackOff example
crashloop_pod = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "name": "crashloop-test",
        "labels": {"app": "crashloop-test"}
    },
    "spec": {
        "containers": [{
            "name": "crasher",
            "image": "busybox",
            "command": ["sh", "-c", "exit 1"]
        }]
    }
}

with open(examples_dir / "crashloop-pod.yaml", "w") as f:
    yaml.dump(crashloop_pod, f)

# 2. ImagePullBackOff example
imagepull_pod = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "name": "imagepull-test",
        "labels": {"app": "imagepull-test"}
    },
    "spec": {
        "containers": [{
            "name": "non-existent",
            "image": "non-existent-image:latest"
        }]
    }
}

with open(examples_dir / "imagepull-pod.yaml", "w") as f:
    yaml.dump(imagepull_pod, f)

# 3. OOMKilled example
oom_pod = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "name": "oom-test",
        "labels": {"app": "oom-test"}
    },
    "spec": {
        "containers": [{
            "name": "memory-hog",
            "image": "polinux/stress",
            "command": ["stress"],
            "args": ["--vm", "1", "--vm-bytes", "500M"],
            "resources": {
                "limits": {"memory": "100Mi"},
                "requests": {"memory": "50Mi"}
            }
        }]
    }
}

with open(examples_dir / "oom-pod.yaml", "w") as f:
    yaml.dump(oom_pod, f)

# 4. Pending pod example
pending_pod = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "name": "pending-test",
        "labels": {"app": "pending-test"}
    },
    "spec": {
        "nodeSelector": {
            "non-existent-node": "true"
        },
        "containers": [{
            "name": "nginx",
            "image": "nginx:latest"
        }]
    }
}

with open(examples_dir / "pending-pod.yaml", "w") as f:
    yaml.dump(pending_pod, f)

# 5. Unavailable deployment example
unavailable_deployment = {
    "apiVersion": "apps/v1",
    "kind": "Deployment",
    "metadata": {
        "name": "unavailable-test",
        "labels": {"app": "unavailable-test"}
    },
    "spec": {
        "replicas": 3,
        "selector": {
            "matchLabels": {"app": "unavailable-test"}
        },
        "template": {
            "metadata": {
                "labels": {"app": "unavailable-test"}
            },
            "spec": {
                "containers": [{
                    "name": "crasher",
                    "image": "busybox",
                    "command": ["sh", "-c", "sleep 5 && exit 1"]
                }]
            }
        }
    }
}

with open(examples_dir / "unavailable-deployment.yaml", "w") as f:
    yaml.dump(unavailable_deployment, f)

print("Example Kubernetes manifests created in examples/k8s/")
print("\nTo test the SRE agent:")
print("1. Apply problematic manifests: kubectl apply -f examples/k8s/")
print("2. Wait a few moments for issues to appear")
print("3. Run the agent: python main.py --namespace default --mode once")
