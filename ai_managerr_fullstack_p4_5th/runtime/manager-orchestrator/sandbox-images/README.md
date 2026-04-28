# Sandbox runner images

These images are intended for `RUNNER_SANDBOX_MODE=docker` execution.

```bash
docker build -t manager-orchestrator-runner-python:latest sandbox-images/python
docker build -t manager-orchestrator-runner-node:latest sandbox-images/node
docker build -t manager-orchestrator-runner-java:latest sandbox-images/java
```

The runtime selects images by detected stack using `RUNNER_SANDBOX_DOCKER_IMAGES`.


## CI/CD
- GitHub Actions workflow: `.github/workflows/sandbox-images.yml`
- Local build helper: `sandbox-images/build-images.sh`
- Recommended registry tags: `latest` + git sha
