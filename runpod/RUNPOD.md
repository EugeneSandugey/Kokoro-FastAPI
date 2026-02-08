# RunPod Platform Reference

## Account
- **User ID**: `user_35mTUmq8sFVkcucqbnG6SZKZQNY`
- **API Key**: Stored in `runpod/.runpod_key` (gitignored)
- **S3 API Key**: Stored in `runpod/.s3_credentials` (gitignored)
  - Access Key: `user_35mTUmq8sFVkcucqbnG6SZKZQNY`
  - Secret: in `.s3_credentials` file
- **Spend Limit**: $80/hr default (contact support to increase)
- **Billing**: Per-second for compute, per-hour for storage

## Pricing Model Explained

| Tier | What It Means | Use Case |
|------|--------------|----------|
| **Community On-Demand** | Cheapest. Individual GPU owners. Runs until you stop. | Quick tests, no network volume |
| **Community Spot** | Even cheaper community. Can be preempted (5s warning). | Throwaway jobs |
| **Secure On-Demand** | RunPod's own data centers. Reliable, network volume support. | Production training |
| **Secure Spot** | Discounted secure. Can be preempted (5s warning). | **Our sweet spot** — cheap + network volumes |

**Why we use Secure Spot**: Network volumes (shared data across pods) ONLY work with Secure Cloud.
Spot pricing gives ~50% discount, and for training with frequent checkpoints, preemption is fine.

Price order: Community Spot < Community < Secure Spot < Secure On-Demand

## GPU Pricing (Feb 2026)

### CRITICAL: Network Volumes Require Secure Cloud
Network volumes only work with Secure Cloud pods. This means community pricing is IRRELEVANT
for our pipeline (which needs shared network volume for data). Use Secure/Secure Spot pricing.

Some GPUs are NOT available in Secure Cloud: RTX 4000 Ada SFF, RTX 4080, RTX 4080 SUPER, RTX 3090 Ti.

### Best Options for F5-TTS Training (~14-16GB VRAM) — Secure Cloud

| GPU | VRAM | Secure On-Demand | Secure Spot | Architecture | GPU Type ID |
|-----|------|-----------------|-------------|--------------|-------------|
| **RTX A5000** | **24GB** | **$0.27/hr** | **$0.14/hr** | **Ampere** | **`NVIDIA RTX A5000`** |
| RTX A4000 | 16GB | $0.25/hr | $0.16/hr | Ampere | `NVIDIA RTX A4000` |
| RTX 4000 Ada | 20GB | $0.26/hr | $0.19/hr | Ada Lovelace | `NVIDIA RTX 4000 Ada Generation` |
| RTX 3090 | 24GB | $0.46/hr | $0.22/hr | Ampere | `NVIDIA GeForce RTX 3090` |
| RTX 4090 | 24GB | $0.59/hr | $0.29/hr | Ada Lovelace | `NVIDIA GeForce RTX 4090` |

**RECOMMENDED: RTX A5000** — 24GB VRAM (plenty of headroom), cheapest secure spot ($0.14/hr).

### Community Cloud Pricing (NO network volume support)

| GPU | VRAM | Community | Comm Spot | GPU Type ID |
|-----|------|-----------|-----------|-------------|
| RTX A4000 | 16GB | $0.17/hr | $0.09/hr | `NVIDIA RTX A4000` |
| RTX 4000 Ada SFF | 20GB | $0.18/hr | $0.09/hr | `NVIDIA RTX 4000 SFF Ada Generation` |
| RTX 3090 | 24GB | $0.22/hr | $0.11/hr | `NVIDIA GeForce RTX 3090` |

### Larger GPUs (Production Training)

| GPU | VRAM | Secure | Secure Spot | GPU Type ID |
|-----|------|--------|-------------|-------------|
| A100 PCIe | 80GB | $1.39/hr | $0.60/hr | `NVIDIA A100 80GB PCIe` |
| A100 SXM | 80GB | $1.49/hr | $0.79/hr | `NVIDIA A100-SXM4-80GB` |
| H100 PCIe | 80GB | $2.39/hr | $1.35/hr | `NVIDIA H100 PCIe` |
| H100 SXM | 80GB | $2.69/hr | $1.50/hr | `NVIDIA H100 80GB HBM3` |

### Cost Estimates for HPO Sweeps (Secure Spot)

| Scenario | GPU | Pricing | Cost |
|----------|-----|---------|------|
| 20 pods × 5 min each | RTX A5000 | Spot $0.14/hr | **$0.23 total** |
| 20 pods × 30 min each | RTX A5000 | Spot $0.14/hr | **$1.40 total** |
| Single 8-hour run | RTX A5000 | Spot $0.14/hr | **$1.12 total** |
| Single 8-hour run | RTX 4090 | Spot $0.29/hr | **$2.32 total** |
| Single 8-hour run | A100 SXM | Spot $0.79/hr | **$6.32 total** |

---

## Pod Types

### Secure Cloud vs Community Cloud
- **Secure Cloud**: T3/T4 data centers, high reliability, redundancy. Higher price.
- **Community Cloud**: Peer-to-peer GPU sharing, vetted hosts. Lower price, less redundancy.
- **Network volumes only work with Secure Cloud pods** (critical limitation).

### Pricing Models
- **On-Demand**: Non-interruptible, pay-as-you-go. Need 1hr balance minimum.
- **Spot**: Interruptible (5-second SIGTERM warning), cheapest. Good for fault-tolerant training.
- **Savings Plans**: 3/6 month commitment, significant discount. Non-refundable.

### Spot Instance Behavior
- Can be terminated with **5-second SIGTERM → SIGKILL** warning
- Volume disk IS retained after interruption
- Must save checkpoints frequently
- Use `interruptible: true` in REST API or spot pricing in SDK

---

## Storage

### Container Disk
- **Temporary** — wiped on pod restart
- $0.10/GB/month (running), free when terminated
- Default: 50GB

### Volume Disk (Pod Volume)
- **Persistent** across pod restarts (not terminations for non-network volumes)
- $0.10/GB/month (running), $0.20/GB/month (stopped)
- Default mount: `/workspace`

### Network Volumes (Key for Our Use Case)
- **Permanent**, portable, survives pod termination
- $0.07/GB/month (≤1TB), $0.05/GB/month (>1TB)
- NVMe SSD backed, 200-400 MB/s typical, up to 10 GB/s peak
- Mount point: `/workspace` (default, replaces pod volume disk)
- **Can be shared between multiple pods** (concurrent read OK, avoid concurrent writes to same file)
- **Cannot be attached after pod deployment** — must attach during creation
- Max size: 4TB
- Size can be increased but NOT decreased

### Network Volume Constraints
- Pods with network volumes **cannot be stopped, only terminated**
- Data at `/workspace` is preserved in network volume after termination
- Deploy new pod with same network volume to regain access

### S3-Compatible API (Upload Data Without Running a Pod)
**NOT Amazon AWS.** This is RunPod's own storage API that happens to use the same protocol as Amazon S3.
Zero extra cost — included with your network volume. Uses `aws` CLI commands but talks to RunPod servers.
Allows uploading/downloading files to network volumes without paying for GPU time.

**Supported Datacenters for S3 API:**
| Datacenter | Endpoint URL |
|------------|-------------|
| EUR-IS-1 | `https://s3api-eur-is-1.runpod.io/` |
| EUR-NO-1 | `https://s3api-eur-no-1.runpod.io/` |
| EU-RO-1 | `https://s3api-eu-ro-1.runpod.io/` |
| EU-CZ-1 | `https://s3api-eu-cz-1.runpod.io/` |
| US-CA-2 | `https://s3api-us-ca-2.runpod.io/` |
| US-GA-2 | `https://s3api-us-ga-2.runpod.io/` |
| US-KS-2 | `https://s3api-us-ks-2.runpod.io/` |
| US-MD-1 | `https://s3api-us-md-1.runpod.io/` |
| US-MO-2 | `https://s3api-us-mo-2.runpod.io/` |
| US-NC-1 | `https://s3api-us-nc-1.runpod.io/` |
| US-NC-2 | `https://s3api-us-nc-2.runpod.io/` |

**IMPORTANT**: To use S3 API for data upload, the network volume MUST be in one of these datacenters.

**S3 API Setup:**
1. Create network volume in supported datacenter
2. Create S3 API key in RunPod console Settings → S3 API Keys (separate from regular API key)
3. Configure AWS CLI: `aws configure` with access key (user ID) + secret
4. Use standard S3 commands with `--endpoint-url` and `--region` flags

**S3 Path Mapping:**
- Pod path: `/workspace/my-folder/file.txt`
- S3 path: `s3://NETWORK_VOLUME_ID/my-folder/file.txt`

**S3 Upload Example:**
```bash
aws s3 cp --region US-KS-2 \
    local_file.tar.gz \
    s3://NETWORK_VOLUME_ID/ \
    --endpoint-url https://s3api-us-ks-2.runpod.io/

# Sync directory
aws s3 sync --region US-KS-2 \
    ./data/ \
    s3://NETWORK_VOLUME_ID/data/ \
    --endpoint-url https://s3api-us-ks-2.runpod.io/
```

**S3 Limitations:**
- Files >500MB must use multipart upload (AWS CLI does this automatically)
- `sync` may have issues with >10,000 files — use individual `cp` for reliability
- No presigned URLs, no versioning, no bucket creation (use RunPod console)

---

## Datacenters

### US Datacenters
| ID | Location | S3 API |
|----|----------|--------|
| US-CA-1 | California | No |
| US-CA-2 | California | **Yes** |
| US-DE-1 | Delaware | No |
| US-GA-1 | Georgia | No |
| US-GA-2 | Georgia | **Yes** |
| US-IL-1 | Illinois | No |
| US-KS-1 | Kansas | No |
| US-KS-2 | Kansas | **Yes** |
| US-KS-3 | Kansas | No |
| US-MD-1 | Maryland | **Yes** |
| US-MO-1 | Missouri | No |
| US-MO-2 | Missouri | **Yes** |
| US-NC-1 | North Carolina | **Yes** |
| US-NC-2 | North Carolina | **Yes** |
| US-NE-1 | Nebraska | No |
| US-OR-1 | Oregon | No |
| US-OR-2 | Oregon | No |
| US-PA-1 | Pennsylvania | No |
| US-TX-1 | Texas | No |
| US-TX-2 | Texas | No |
| US-TX-3 | Texas | No |
| US-TX-4 | Texas | No |
| US-TX-5 | Texas | No |
| US-WA-1 | Washington | No |

### Recommended Datacenter: **US-KS-2**
- Has S3 API support (upload data without running a pod)
- Central US location (good latency)
- Good availability for community GPUs
- Listed in REST API's datacenter enum

---

## Python SDK Reference

### Installation
```bash
pip install runpod
```

### Authentication
```python
import runpod
runpod.api_key = open('runpod/.runpod_key').read().strip()
# Or: runpod.api_key = os.getenv("RUNPOD_API_KEY")
```

### Available Functions
```python
# Account
runpod.get_user()        # Returns: {id, pubKey, networkVolumes: [{id, name, size, dataCenterId}]}

# GPUs
runpod.get_gpus()        # List all GPU types
runpod.get_gpu(gpu_id)   # Get specific GPU details + pricing

# Pods
runpod.create_pod(...)   # Create and deploy a pod
runpod.get_pods()        # List all pods
runpod.get_pod(pod_id)   # Get specific pod
runpod.stop_pod(pod_id)  # Stop a pod
runpod.resume_pod(pod_id)  # Resume a stopped pod
runpod.terminate_pod(pod_id)  # Permanently delete a pod

# Templates
runpod.create_template(name, image_name)
```

### create_pod Parameters
```python
runpod.create_pod(
    name="my-pod",                    # Pod name (not unique required)
    image_name="my-image:tag",        # Docker image (or use template_id)
    gpu_type_id="NVIDIA GeForce RTX 3090",  # GPU type string
    cloud_type="ALL",                 # "ALL" | "COMMUNITY" | "SECURE"
    support_public_ip=True,           # Public IP for SSH
    start_ssh=True,                   # Enable SSH
    data_center_id=None,              # Lock to specific DC (auto-resolved from network volume)
    country_code=None,                # Lock to country
    gpu_count=1,                      # Number of GPUs
    volume_in_gb=0,                   # Pod volume size (0 if using network volume)
    container_disk_in_gb=10,          # Container disk size (default 10, wiped on restart)
    min_vcpu_count=1,                 # Min vCPUs
    min_memory_in_gb=1,               # Min RAM
    docker_args="",                   # Docker run arguments
    ports="8888/http,22/tcp",         # Exposed ports
    volume_mount_path="/workspace",   # Where to mount volume
    env={"KEY": "value"},             # Environment variables
    template_id=None,                 # Use template instead of image
    network_volume_id=None,           # Attach network volume
    allowed_cuda_versions=None,       # e.g. ["12.4"]
)
```

**IMPORTANT**: If `network_volume_id` is set and `data_center_id` is None, the SDK automatically resolves the datacenter from the network volume. No need to specify both.

### SDK Does NOT Support
- Network volume creation (use REST API)
- S3 API operations (use boto3/AWS CLI)
- Spot/interruptible pods (use REST API with `interruptible: true`)

---

## REST API Reference

### Base URL
`https://rest.runpod.io/v1/`

### Authentication
```
Authorization: Bearer RUNPOD_API_KEY
```

### Create Network Volume
```bash
curl --request POST \
  --url https://rest.runpod.io/v1/networkvolumes \
  --header 'Authorization: Bearer API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
    "dataCenterId": "US-KS-2",
    "name": "f5tts-training-data",
    "size": 20
  }'
# Returns: {"id": "abc123", "size": 20}
```

### Create Pod (REST API — supports interruptible/spot)
```bash
curl --request POST \
  --url https://rest.runpod.io/v1/pods \
  --header 'Authorization: Bearer API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
    "name": "f5tts-sweep-001",
    "imageName": "username/f5tts-train:latest",
    "gpuTypeIds": ["NVIDIA RTX A4000"],
    "gpuTypePriority": "availability",
    "cloudType": "COMMUNITY",
    "interruptible": true,
    "containerDiskInGb": 20,
    "volumeInGb": 0,
    "networkVolumeId": "VOLUME_ID",
    "env": {"LR": "5e-6", "STEPS": "1000"},
    "ports": ["22/tcp"],
    "dataCenterIds": ["US-KS-2"],
    "allowedCudaVersions": ["12.4"]
  }'
```

### Pod Lifecycle
```bash
# List pods
curl https://rest.runpod.io/v1/pods -H 'Authorization: Bearer API_KEY'

# Get pod by ID
curl https://rest.runpod.io/v1/pods/POD_ID -H 'Authorization: Bearer API_KEY'

# Stop pod
curl -X POST https://rest.runpod.io/v1/pods/POD_ID/stop -H 'Authorization: Bearer API_KEY'

# Start/Resume pod
curl -X POST https://rest.runpod.io/v1/pods/POD_ID/start -H 'Authorization: Bearer API_KEY'

# Terminate (delete) pod
curl -X DELETE https://rest.runpod.io/v1/pods/POD_ID -H 'Authorization: Bearer API_KEY'
```

### Network Volume Operations
```bash
# List volumes
curl https://rest.runpod.io/v1/networkvolumes -H 'Authorization: Bearer API_KEY'

# Get volume by ID
curl https://rest.runpod.io/v1/networkvolumes/VOL_ID -H 'Authorization: Bearer API_KEY'

# Update volume (resize)
curl -X PATCH https://rest.runpod.io/v1/networkvolumes/VOL_ID \
  -H 'Authorization: Bearer API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"size": 50}'

# Delete volume
curl -X DELETE https://rest.runpod.io/v1/networkvolumes/VOL_ID -H 'Authorization: Bearer API_KEY'
```

---

## GraphQL API

### Endpoint
`https://api.runpod.io/graphql`

### Authentication
```
Authorization: Bearer RUNPOD_API_KEY
```

### Useful Queries
```graphql
# Get all GPU types with pricing
query {
  gpuTypes {
    id
    displayName
    memoryInGb
    communityPrice
    securePrice
    communitySpotPrice
    secureSpotPrice
  }
}

# Get user info + network volumes
query {
  myself {
    id
    pubKey
    networkVolumes {
      id
      name
      size
      dataCenterId
    }
  }
}
```

---

## Templates

Templates are pre-configured Docker image setups for quick pod deployment.

### Types
- **Official**: Curated by RunPod, tested, supported
- **Community**: Created by users, no official support
- **Custom**: Your own private or public templates

### Create Template via SDK
```python
template = runpod.create_template(
    name="f5tts-training",
    image_name="username/f5tts-train:latest"
)
# Returns: {id, name, imageName, containerDiskInGb, volumeInGb, volumeMountPath, ports, env}
```

### Template Contents
- Container image (Docker image tag)
- Hardware specs (disk sizes, mount paths)
- Network settings (exposed ports)
- Environment variables
- Startup commands (docker entrypoint/cmd)

---

## Docker Image Requirements

### CUDA Compatibility
- Host CUDA must match or exceed image CUDA version
- Use `allowedCudaVersions` to filter compatible machines
- Our image: CUDA 12.4 → filter for ≥12.4

### Building for RunPod
- Always build with `--platform linux/amd64` (especially from Mac)
- RunPod manages Docker daemon — cannot run Docker inside a pod
- Use custom templates for custom Docker images

### Image Considerations
- Smaller images = faster cold starts
- Pre-install all dependencies in image
- Use `/workspace` for persistent data (network volume mount)
- Avoid installing to `/workspace` in Dockerfile (gets overwritten by volume)

---

## Connecting to Pods

### SSH
- Pods expose SSH on a mapped port (e.g., internal 22 → public 10341)
- Public IP + mapped port shown in pod details
- Key-based auth recommended

### Web Terminal
- Available in RunPod console for each pod
- No local setup needed

### JupyterLab
- Many templates include JupyterLab on port 8888

### VSCode/Cursor
- SSH Remote extension can connect directly to pods

---

## Monitoring & Troubleshooting

### Pod Logs
- **Container logs**: stdout/stderr from your application
- **System logs**: Pod lifecycle (creation, image download, startup, shutdown)
- View via RunPod console → Pods → expand pod → Logs

### Common Issues
| Issue | Solution |
|-------|----------|
| Pod stuck on initializing | Check if command is invalid or missing `sleep infinity` |
| OCI runtime create failed | CUDA version mismatch — use `allowedCudaVersions` filter |
| Zero GPU on restart | GPU released when stopped, may get 0 GPU on start |
| Docker daemon error | Can't run Docker inside pod — use custom template |
| S3 SignatureDoesNotMatch | Check AWS CLI credentials, ensure S3 key (not API key) |
| S3 502 bad gateway | Set `AWS_MAX_ATTEMPTS=10` and `AWS_RETRY_MODE=standard` |

### Stop vs Terminate
- **Stop**: Container disk wiped, volume disk preserved, still charged for volume storage ($0.20/GB/mo)
- **Terminate**: Everything deleted EXCEPT network volume data. No ongoing charges.
- **Network volume pods cannot be stopped** — only terminated

### Auto-Stop
```bash
# Stop pod after 2 hours
nohup bash -c "sleep 2h; runpodctl stop pod $RUNPOD_POD_ID" &
```

---

## Our Pipeline Architecture

### Training Image
- Base: `pytorch/pytorch:2.4.0-cuda12.4-cudnn9-devel` (Python 3.11)
- F5-TTS installed at `/app/F5-TTS/` (NOT `/workspace/`)
- Config `F5TTS_RunPod_Base.yaml` baked in
- F5-TTS pinned to commit `655fbca5529b68e36d7b8f2d6d131f68132156fe`

### Data Flow
1. Network Volume at `/workspace` contains:
   - `data/` — prepared training datasets (raw.arrow + audio files)
   - `ckpts/` — pretrained weights + experiment checkpoints
2. Entrypoint symlinks `/app/F5-TTS/data/` → `/workspace/data/`
3. Pretrained weights COPIED (not symlinked) to checkpoint dir
4. Training runs, saves checkpoints to `/workspace/ckpts/EXPERIMENT_NAME/`

### Sweep Configuration (via env vars)
- `EXPERIMENT_NAME`: Unique name for this run
- `LEARNING_RATE`: LR override
- `BATCH_SIZE`: Batch size in frames
- `MAX_UPDATES`: Number of training steps
- `SAVE_EVERY`: Checkpoint frequency

### Key Files
| File | Purpose |
|------|---------|
| `runpod/Dockerfile` | Training image (~17GB) |
| `runpod/entrypoint.sh` | Pod startup: symlinks, weight copy, training |
| `runpod/sweep.py` | CLI: launch/monitor/cleanup/results/status |
| `runpod/prepare_volume.py` | One-time volume data setup |
| `runpod/F5TTS_RunPod_Base.yaml` | Base config (baked into image) |
| `runpod/configs/*.yaml` | Sweep configs |

### Critical Reminders
- `raw.arrow` has HARDCODED audio paths — must re-prepare for `/app/F5-TTS/data/...` paths
- Architecture: `text_mask_padding: false`, `pe_attn_head: 1` MUST match pretrained
- Pretrained weights MUST be copied, not symlinked
- Container disk for temporary files only — all important data on network volume
