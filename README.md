# Student Study AI Agent OCR

Internal CPU-based OCR service for the Student Study AI Agent. It uses RapidOCR
with PP-OCRv6 small models and runs as a single-replica ClusterIP service.
Images are built for `linux/amd64` and deployed by digest through GitHub Actions.

## API

- `GET /` serves the image upload and OCR evaluation page
- `GET /health/live`
- `GET /health/ready`
- `GET /version`
- `POST /v1/ocr` with multipart field `image` (JPEG, PNG, or WebP; up to 10 MiB)
- `POST /v1/ocr/raw` with the image bytes as the request body and the image MIME type
  as `Content-Type` (JPEG, PNG, or WebP; up to 10 MiB)

The OCR response includes image dimensions and ordered text blocks with bounding
boxes, OCR confidence scores, and `writingType` (`printed`, `handwritten`, or
`unknown`) with a separate `writingTypeConfidence`. The latter is a classifier
score, not an accuracy guarantee. Image contents and OCR text are not logged.
The experimental handwriting classifier is the MIT-licensed
[Ankygtm/Handwriting-Classifier](https://github.com/Ankygtm/Handwriting-Classifier),
pinned to a specific commit and running locally on CPU. Its training domain is
Ukrainian text; accuracy on Chinese homework images has not been validated, so
verify classifications against representative local samples before relying on
them. A synthetic printed-number smoke test was misclassified as handwritten
with 99.96% confidence, so even high scores can be wrong. Low-confidence
classifications are returned as `unknown`.
The upload page can compare recognized text against a manually entered reference
using character-level accuracy (ignoring whitespace). This is a sample-level
measurement, not a semantic correctness score. The current general OCR model
does not interpret handwritten math or the meaning of Chinese proofreading,
circle, check, and cross marks; those should be reviewed against the original
image.

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

The service is exposed to the local network through the K3s Traefik Ingress at:

```text
https://student-study-ai-agent-orc.home.local
```

The TLS certificate must exist in the `student-study-ai-agent-orc-tls` Secret
in the `student-study-ai-agent-ocr` namespace. The NetworkPolicy permits ingress
from the Traefik controller, the dev, QA, and production application namespaces.

To check a deployment:

```powershell
kubectl -n student-study-ai-agent-ocr get pods,services
kubectl -n student-study-ai-agent-ocr rollout status deployment/student-study-ai-agent-ocr
```
