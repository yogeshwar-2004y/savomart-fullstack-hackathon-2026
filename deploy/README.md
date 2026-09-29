# Azure demo deployment

The hackathon deployment runs on one Ubuntu VM in `rg-savo-sitescout-demo` (South India). Docker Compose starts PostGIS, Redis, the FastAPI API, the RQ worker, and the React build behind Caddy. Caddy serves HTTPS with an outer shared Basic Auth gate and proxies `/api/*` to the private API container. Only ports 80 and 443 are public; SSH is limited to the deploying machine's IP by the Azure network security group. This is a cost-conscious demo, not a production architecture.

URL: https://savo-sitescout-yogesh-2026.southindia.cloudapp.azure.com/

The shared login name is `sitescout`. The password is in the locally ignored `.deploy/demo-password` file on the deploying machine; do not commit or paste it into tickets, logs, or screenshots. The VM's SSH private key and the environment file are also ignored. Browser role switching remains a **demo identity** control. The shared login does not enforce individual identity, so do not expose real customer, property, or confidential store data to this deployment.

## Operations

From the repository root on the deploying machine:

```bash
ssh -o UserKnownHostsFile=.deploy/known_hosts -i .deploy/azure-demo-ed25519 azureuser@savo-sitescout-yogesh-2026.southindia.cloudapp.azure.com
```

On the VM:

```bash
cd /home/azureuser/sitescout
sudo docker compose --env-file .env.azure -f deploy/docker-compose.azure.yml ps
sudo docker compose --env-file .env.azure -f deploy/docker-compose.azure.yml logs --tail=100 api worker frontend
sudo docker compose --env-file .env.azure -f deploy/docker-compose.azure.yml exec -T api alembic upgrade head
sudo docker compose --env-file .env.azure -f deploy/docker-compose.azure.yml exec -T -e PYTHONPATH=/app api python scripts/verify_full_workflow.py
```

Check the public health endpoint from the deploying machine without putting the password in command history:

```bash
curl -fsS -u "sitescout:$(cat .deploy/demo-password)" https://savo-sitescout-yogesh-2026.southindia.cloudapp.azure.com/api/v1/health
```

The operational-store source on this VM is the labelled provided snapshot, not a live internal-service connection. No store-service token is installed. OSM lookups can use the configured public services and Redis cache; simulated signal fallback is enabled and remains labelled on affected evidence. The GCC ward and 2011 census seeds are loaded. The database, Redis, uploaded photos, and Caddy certificates live in Docker volumes on the VM; there is no automated off-VM backup. Rebuilding containers retains volumes, but deleting the resource group or Compose volumes destroys this data.

## Credit control

The VM is `Standard_B2s_v2` with a 64 GB Standard SSD and a static Standard public IP. The observed compute list price was approximately USD 0.117/hour (about USD 84 for 30 days), **before** disk, IP, bandwidth, taxes, and any pricing adjustments. Azure free credit is not a guarantee that this deployment is free. Monitor Cost Management and set a budget alert in the Azure portal.

Stop VM compute when the demo is idle:

```bash
az vm deallocate -g rg-savo-sitescout-demo -n vm-savo-sitescout-demo
```

Restart it before a demo:

```bash
az vm start -g rg-savo-sitescout-demo -n vm-savo-sitescout-demo
```

Deallocation stops compute billing but the disk and static public IP can still cost money. Do not delete the resource group unless the persisted demo data and uploaded photos are no longer needed.

## Production gaps

Replace shared Basic Auth and demo role headers with per-user authentication and authorization; arrange backups, monitoring, secret storage/rotation, private networking for external dependencies, image pinning, and a managed deployment/update process before handling real operational data. This runbook does not claim that scripted workflow observations or simulated scoring inputs are live field evidence.
