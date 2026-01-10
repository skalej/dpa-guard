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

## 4) Managing secrets safely (Vault + External Secrets Operator)

**Do not store real passwords/tokens in Git.**  
Argo CD can only apply what’s in Git, so to keep secrets out of Git we use:

- **Vault**: stores secret values (passwords/tokens/keys)
- **External Secrets Operator (ESO)**: reads from Vault and creates Kubernetes `Secret` objects
- **Argo CD**: applies only *safe* manifests (SecretStore / ExternalSecret) from Git

> For local dev, Vault can run in **dev mode**. This is **not** production-safe (single pod, root token, no HA).

### 4.1 Install Vault (local dev mode)

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update

kubectl create namespace vault --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install vault hashicorp/vault \
  --namespace vault \
  --set "server.dev.enabled=true" \
  --set "ui.enabled=true"
```

Access Vault UI/API locally:

```bash
kubectl -n vault port-forward svc/vault 8200:8200
# UI/API: http://localhost:8200
```

### 4.2 Write secrets into Vault (KV v2)

Exec into the Vault pod and login:

```bash
kubectl -n vault exec -it vault-0 -- /bin/sh
export VAULT_ADDR='http://127.0.0.1:8200'
vault login <ROOT_TOKEN>
```

Enable KV v2 at `secret/` (if not already enabled):

```bash
vault secrets enable -path=secret kv-v2
```

Example: store MinIO credentials under `secret/dpa/minio`:

```bash
vault kv put secret/dpa/minio rootUser="user" rootPassword="password"
```

### 4.3 Enable Kubernetes auth in Vault (so ESO can authenticate)

Inside the Vault pod:

```bash
vault auth enable kubernetes

vault write auth/kubernetes/config \
  kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
  token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"
```

Create a policy allowing read access to `secret/dpa/*`:

```bash
vault policy write dpa-read - << 'EOF'
path "secret/data/dpa/*" {
  capabilities = ["read"]
}
path "secret/metadata/dpa/*" {
  capabilities = ["list"]
}
EOF
```

Create a ServiceAccount in the `dpa` namespace that ESO will use:

```bash
kubectl -n dpa create serviceaccount external-secrets-sa
```

Bind a Vault role to that ServiceAccount:

```bash
vault write auth/kubernetes/role/dpa-eso \
  bound_service_account_names="external-secrets-sa" \
  bound_service_account_namespaces="dpa" \
  policies="dpa-read" \
  ttl="1h"
```

### 4.4 Install External Secrets Operator (ESO)

```bash
kubectl create namespace external-secrets --dry-run=client -o yaml | kubectl apply -f -

helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm upgrade --install external-secrets external-secrets/external-secrets \
  -n external-secrets
```

### 4.5 Create a Vault SecretStore (GitOps-safe)

Create `infra/k8s/secrets/secretstore-vault.yaml`:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: dpa
spec:
  provider:
    vault:
      server: "http://vault.vault.svc.cluster.local:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "dpa-eso"
          serviceAccountRef:
            name: "external-secrets-sa"
```

Apply:

```bash
kubectl apply -f infra/k8s/secrets/secretstore-vault.yaml
```

### 4.6 Create ExternalSecrets (Vault → K8s Secret)

Create `infra/k8s/secrets/minio-external-secret.yaml`:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: minio-creds
  namespace: dpa
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: minio-creds
    creationPolicy: Owner
  data:
    - secretKey: rootUser
      remoteRef:
        key: dpa/minio
        property: rootUser
    - secretKey: rootPassword
      remoteRef:
        key: dpa/minio
        property: rootPassword
```

Apply:

```bash
kubectl apply -f infra/k8s/secrets/minio-external-secret.yaml
kubectl apply -f infra/k8s/secrets/postgres-external-secret.yaml
```

Verify ESO created Kubernetes Secrets:

```bash
kubectl -n dpa get secret minio-creds postgres-creds
```