# Savo SiteScout — Azure Cloud Deployment Guide

This guide walks you step-by-step through deploying the complete **Savo SiteScout** platform to **Microsoft Azure** using your $200 free credits.

---

## Architecture Overview on Azure

| Component | Azure Service | Description | Estimated Monthly Cost |
|---|---|---|---|
| **Frontend SPA** | **Azure Static Web Apps** | React 19 + Vite static site with global CDN & SSL | **Free** ($0) |
| **Backend API** | **Azure Container Apps (ACA)** | FastAPI Docker container with auto-HTTPS | ~$5 - $10 (free tier includes 180k vCPU-sec) |
| **RQ Worker** | **Azure Container Apps** | Python worker for background scoring & Overpass fetch | ~$5 - $10 |
| **Database** | **Azure Database for PostgreSQL** | Flexible Server (B1ms burstable) + PostGIS 16 | ~$15 - $25 |
| **Redis Cache** | **Azure Cache for Redis** (Basic C0) or Container App | In-memory message queue & caching | ~$0 (as Container) or ~$16 (Managed) |

---

## Method 1: Cloud-Native Deployment (Azure Container Apps + Static Web Apps)

### Step 1: Install & Login to Azure CLI
If you haven't installed Azure CLI locally:
```bash
# macOS (Homebrew)
brew install azure-cli

# Login to your Azure account (opens browser)
az login
```

Set your active subscription (where your $200 credit is active):
```bash
az account list --output table
az account set --subscription "<YOUR_SUBSCRIPTION_NAME_OR_ID>"
```

---

### Step 2: Create a Resource Group
Create a resource group in a low-latency region (e.g., `centralindia`, `southeastasia`, or `eastus`):
```bash
export RG_NAME="savo-sitescout-rg"
export LOCATION="centralindia"

az group create --name $RG_NAME --location $LOCATION
```

---

### Step 3: Create Azure Database for PostgreSQL (with PostGIS)
1. **Create PostgreSQL Flexible Server**:
   ```bash
   export DB_SERVER_NAME="savo-postgres-$RANDOM"
   export DB_ADMIN_USER="sitescout"
   export DB_ADMIN_PASSWORD="SiteScout_Secure_Pass_2026!"

   az postgres flexible-server create \
     --resource-group $RG_NAME \
     --name $DB_SERVER_NAME \
     --location $LOCATION \
     --admin-user $DB_ADMIN_USER \
     --admin-password $DB_ADMIN_PASSWORD \
     --sku-name Standard_B1ms \
     --tier Burstable \
     --version 16 \
     --storage-size 32 \
     --database-name sitescout \
     --public-access 0.0.0.0
   ```

2. **Enable PostGIS Extension**:
   ```bash
   az postgres flexible-server parameter set \
     --resource-group $RG_NAME \
     --server-name $DB_SERVER_NAME \
     --name azure.extensions \
     --value POSTGIS
   ```

3. **Allow Azure Services Firewall Access**:
   ```bash
   az postgres flexible-server firewall-rule create \
     --resource-group $RG_NAME \
     --name $DB_SERVER_NAME \
     --rule-name AllowAllAzureServices \
     --start-ip-address 0.0.0.0 \
     --end-ip-address 0.0.0.0
   ```

---

### Step 4: Create Azure Container Registry (ACR) & Build Images
1. **Create Container Registry**:
   ```bash
   export ACR_NAME="savoregistry$RANDOM"

   az acr create \
     --resource-group $RG_NAME \
     --name $ACR_NAME \
     --sku Basic \
     --admin-enabled true
   ```

2. **Build and Push the Backend Image directly in Azure (no local Docker build needed)**:
   ```bash
   az acr build \
     --registry $ACR_NAME \
     --image sitescout-backend:latest \
     ./backend
   ```

3. **Retrieve ACR Credentials**:
   ```bash
   export ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
   export ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query "loginServer" -o tsv)
   ```

---

### Step 5: Create Azure Container Apps Environment & Deploy Services
1. **Create Container Apps Managed Environment**:
   ```bash
   export ENVIRONMENT_NAME="savo-env"

   az containerapp env create \
     --name $ENVIRONMENT_NAME \
     --resource-group $RG_NAME \
     --location $LOCATION
   ```

2. **Deploy Redis Container**:
   ```bash
   az containerapp create \
     --name sitescout-redis \
     --resource-group $RG_NAME \
     --environment $ENVIRONMENT_NAME \
     --image redis:7-alpine \
     --target-port 6379 \
     --ingress internal \
     --min-replicas 1 \
     --max-replicas 1 \
     --cpu 0.25 --memory 0.5Gi
   ```

3. **Construct Connection Strings**:
   ```bash
   export DATABASE_URL="postgresql+psycopg://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${DB_SERVER_NAME}.postgres.database.azure.com:5432/sitescout?sslmode=require"
   export REDIS_URL="redis://sitescout-redis:6379/0"
   ```

4. **Deploy FastAPI Backend API**:
   ```bash
   az containerapp create \
     --name sitescout-api \
     --resource-group $RG_NAME \
     --environment $ENVIRONMENT_NAME \
     --image $ACR_LOGIN_SERVER/sitescout-backend:latest \
     --registry-server $ACR_LOGIN_SERVER \
     --registry-username $ACR_NAME \
     --registry-password $ACR_PASSWORD \
     --target-port 8000 \
     --ingress external \
     --min-replicas 1 \
     --max-replicas 3 \
     --cpu 0.5 --memory 1.0Gi \
     --env-vars \
       ENVIRONMENT="production" \
       DATABASE_URL="$DATABASE_URL" \
       REDIS_URL="$REDIS_URL" \
       CORS_ORIGINS="*" \
       ALLOW_SIMULATED_SIGNAL_FALLBACK="true"
   ```

5. **Deploy RQ Background Worker**:
   ```bash
   az containerapp create \
     --name sitescout-worker \
     --resource-group $RG_NAME \
     --environment $ENVIRONMENT_NAME \
     --image $ACR_LOGIN_SERVER/sitescout-backend:latest \
     --registry-server $ACR_LOGIN_SERVER \
     --registry-username $ACR_NAME \
     --registry-password $ACR_PASSWORD \
     --min-replicas 1 \
     --max-replicas 1 \
     --cpu 0.5 --memory 1.0Gi \
     --command python -m app.jobs.worker \
     --env-vars \
       ENVIRONMENT="production" \
       DATABASE_URL="$DATABASE_URL" \
       REDIS_URL="$REDIS_URL" \
       ALLOW_SIMULATED_SIGNAL_FALLBACK="true"
   ```

6. **Get your Deployed Backend API URL**:
   ```bash
   export API_URL=$(az containerapp show --name sitescout-api --resource-group $RG_NAME --query "properties.configuration.ingress.fqdn" -o tsv)
   echo "Backend API URL: https://${API_URL}"
   ```

---

### Step 6: Initialize Database Schema & Seed Data
Run migrations and seed the Chennai store baseline:
```bash
az containerapp exec \
  --name sitescout-api \
  --resource-group $RG_NAME \
  --command "alembic upgrade head && python scripts/seed_chennai_data.py"
```

Verify backend health:
```bash
curl -i "https://${API_URL}/api/v1/health"
```

---

### Step 7: Deploy React Frontend to Azure Static Web Apps (Free)
1. **Create Azure Static Web App linked to your GitHub repo**:
   ```bash
   az staticwebapp create \
     --name savo-sitescout-frontend \
     --resource-group $RG_NAME \
     --location "eastasia" \
     --source https://github.com/yogeshwar-2004y/savomart-fullstack-hackathon-2026 \
     --branch main \
     --app-location "frontend" \
     --output-location "dist" \
     --login-with-github
   ```

2. **Set Environment Variable for the API Backend**:
   ```bash
   az staticwebapp appsettings set \
     --name savo-sitescout-frontend \
     --resource-group $RG_NAME \
     --setting-names VITE_API_BASE_URL="https://${API_URL}"
   ```

Azure Static Web Apps will create a GitHub Actions workflow in `.github/workflows/` that automatically builds and deploys your frontend on every push.

---

## Method 2: Fast Single-VM Deployment on Azure (Ubuntu + Docker Compose)

If you want the quickest 5-minute deployment using the existing `docker-compose.yml`:

1. **Create an Ubuntu VM** (Size: `Standard_B2s` - 2 vCPU, 4GB RAM, ~$30/month):
   ```bash
   az vm create \
     --resource-group $RG_NAME \
     --name savo-vm \
     --image Ubuntu2204 \
     --size Standard_B2s \
     --admin-username azureuser \
     --generate-ssh-keys \
     --public-ip-sku Standard
   ```

2. **Open Inbound Web Ports (80, 443, 5173, 8000)**:
   ```bash
   az vm open-port --resource-group $RG_NAME --name savo-vm --port 80 --priority 1001
   az vm open-port --resource-group $RG_NAME --name savo-vm --port 5173 --priority 1002
   az vm open-port --resource-group $RG_NAME --name savo-vm --port 8000 --priority 1003
   ```

3. **SSH into the VM & Run Savo**:
   ```bash
   export VM_IP=$(az vm show -d -g $RG_NAME -n savo-vm --query publicIps -o tsv)
   ssh azureuser@$VM_IP
   ```

   Inside the VM terminal:
   ```bash
   # 1. Install Docker & Docker Compose
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-v2 git
   sudo usermod -aG docker $USER
   newgrp docker

   # 2. Clone repository
   git clone https://github.com/yogeshwar-2004y/savomart-fullstack-hackathon-2026.git savo
   cd savo

   # 3. Create .env
   cp .env.example .env

   # 4. Start all 5 services in background
   docker compose up -d --build

   # 5. Run migrations & seed data
   docker compose exec api alembic upgrade head
   docker compose exec api python scripts/seed_chennai_data.py
   ```

4. **Access Savo SiteScout**:
   - Frontend UI: `http://<VM_IP>:5173`
   - Backend API: `http://<VM_IP>:8000/api/v1/health`
   - Interactive Docs: `http://<VM_IP>:8000/docs`

---

## PostGIS Verification on Azure
To verify PostGIS spatial indexing on your deployed database:
```sql
SELECT postgis_full_version();
```
Output confirms PostGIS 3.4+ spatial functions (`ST_Contains`, `ST_Buffer`, `ST_Distance`) are fully operational.
