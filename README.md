# Student Study AI Agent OCR

Internal CPU-based OCR service for the Student Study AI Agent. It uses RapidOCR
with PP-OCRv5 mobile models and runs as a single-replica ClusterIP service.
Images are built for `linux/amd64` and deployed by digest through GitHub Actions.

## API

- `GET /health/live`
- `GET /health/ready`
- `GET /version`
- `POST /v1/ocr` with multipart field `image` (JPEG, PNG, or WebP; up to 10 MiB)

The OCR response includes image dimensions and ordered text blocks with bounding
boxes and confidence scores. Image contents and OCR text are not logged.

## Deployment

Pushing to `main` builds and pushes an immutable
`ghcr.io/itrice/student-study-ai-agent-ocr-service` image, then deploys it to
the existing K3s cluster using the `Student-Study-OCR-Runner` self-hosted runner. The workflow
requires access to GHCR and a runner with `kubectl` configured for the cluster.
Add repository Actions secrets `GHCR_PULL_USERNAME` and `GHCR_PULL_TOKEN` with
a GHCR identity that has read access to the private image package. The token is
used to create or refresh the `ghcr-pull` Kubernetes Secret.

The Kubernetes manifests are in `k8s/`. The internal service address is:

```text
http://student-study-ai-agent-ocr.student-study-ai-agent-ocr.svc.cluster.local:8000
```

Ingress, LoadBalancer, and NodePort are intentionally not configured. The
NetworkPolicy permits ingress only from the dev, QA, and production application
namespaces.

To check a deployment:

```powershell
kubectl -n student-study-ai-agent-ocr get pods,services
kubectl -n student-study-ai-agent-ocr rollout status deployment/student-study-ai-agent-ocr
```
