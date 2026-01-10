# DPA Guard — Local Dev Environment Setup (Kubernetes + Helm + Argo CD)

This repo uses a **local Kubernetes cluster** (Kind) and **Argo CD** (GitOps) to run infrastructure services:

- **Postgres** (database)
- **Redis** (queue/cache)
- **MinIO** (S3-compatible object storage)

> Goal: get your local environment + infra running reliably.  
> Once infra is up, you can deploy the API and Web apps (next steps).


## Prerequisites

### Required tools (macOS)

```bash
brew install kubectl helm kind argocd
```

Verify installs:
```bash
kubectl version --client
helm version
kind version
argocd version
```


## Repo layout (high level)

```
infra/
  k8s/                  # Kubernetes manifests (apps deployed by Argo CD)
  argocd/
    projects/           # Argo CD AppProjects (permissions boundary)
    apps/               # Argo CD Applications (infra + later api/web)
services/
  api/                  # FastAPI service (later step)
apps/
  web/                  # Next.js UI (later step)
```


## 1) Create local Kubernetes cluster (Kind)

### 1.1 Create the cluster

```bash
kind create cluster --name dpa-guard --config infra/k8s/kind-config.yaml
kubectl cluster-info
```

### 1.2 Create namespaces

```bash
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace dpa --dry-run=client -o yaml | kubectl apply -f -
```


## 2) Install Argo CD

### 2.1 Install Argo CD into the cluster

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Wait for the main components:

```bash
kubectl -n argocd rollout status deploy/argocd-server --timeout=180s
kubectl -n argocd rollout status deploy/argocd-repo-server --timeout=180s
kubectl -n argocd rollout status deploy/argocd-application-controller --timeout=180s
```

### 2.2 Access Argo CD UI locally

Port-forward:

```bash
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

Open in browser:

- https://localhost:8080

### 2.3 Login (admin)

Get initial admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo
```

Login via CLI (Argo CD server uses a self-signed cert in local installs):

```bash
argocd login localhost:8080 --username admin --password <PASTE_PASSWORD> --insecure
```

## 3) Bootstrap GitOps (AppProject + Applications)

Argo CD must pull manifests from a **remote Git repo** (GitHub/GitLab/etc.). It cannot read your local filesystem.

### 3.1 Create / set your remote repo

If you haven’t pushed yet:

```bash
git add .
git commit -m "Initial skeleton"
git branch -M main
git remote add origin <YOUR_REMOTE_REPO_URL>
git push -u origin main
```

### 3.2 Configure `root-app.yaml` (repoURL)

Edit:

- `infra/argocd/root-app.yaml`

Replace:

- `repoURL: REPLACE_ME_WITH_YOUR_GIT_REPO_URL`

with your real repo URL (example):

- `repoURL: https://github.com/<you>/dpa-guard.git`

Commit and push:

```bash
git add infra/argocd/root-app.yaml
git commit -m "Configure Argo root app repoURL"
git push
```

### 3.3 Apply AppProject + Root App

```bash
kubectl -n argocd apply -f infra/argocd/projects/dpa-guard-project.yaml
kubectl -n argocd apply -f infra/argocd/root-app.yaml
```

Watch apps:

```bash
argocd app list
```

Watch workloads:

```bash
kubectl -n dpa get pods -w
```