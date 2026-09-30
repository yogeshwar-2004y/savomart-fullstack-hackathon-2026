# Azure demo deployment

The hackathon deployment runs on one Ubuntu VM in `rg-savo-sitescout-demo` (South India). Docker Compose starts PostGIS, Redis, the FastAPI API, the RQ worker, and the React build behind Caddy. Caddy serves HTTPS with an outer shared Basic Auth gate and proxies `/api/*` to the private API container. Only ports 80 and 443 are public; SSH is limited to the deploying machine's IP by the Azure network security group. This is a cost-conscious demo, not a production architecture.

URL: https://savo-sitescout-yogesh-2026.southindia.cloudapp.azure.com/

The shared login name is `sitescout`. The password is in the locally ignored `.deploy/demo-password` file on the deploying machine; do not commit or paste it into tickets, logs, or screenshots. The VM's SSH private key and the environment file are also ignored. Browser role switching remains a **demo identity** control. The shared login does not enforce individual identity, so do not expose real customer, property, or confidential store data to this deployment.

The sitescout sign-in is a temporary gate for the public Azure demo. The app’s in-page role selector is demo identity, not authentication; the shared password prevents unrestricted access but does not provide separate user accounts.

USERNAME : sitescout
PASSWORD : 489bb61ee98e810b8115aea7ec9e034d5f276d4c9178c697

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
