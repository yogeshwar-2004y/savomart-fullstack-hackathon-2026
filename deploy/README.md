# Retired Azure demo deployment

The hackathon deployment was retired on 2026-10-04. Azure confirmed that `rg-savo-sitescout-demo` no longer exists, and the former DNS name no longer resolves. The VM, disk, public IP, NIC, VNet, and network security group were deleted. The following is a record of the former setup, not a live operations guide.

The demo ran on one Ubuntu VM in South India. Docker Compose started PostGIS, Redis, the FastAPI API, the RQ worker, and the React build behind Caddy. Caddy served HTTPS with an outer shared Basic Auth gate and proxied `/api/*` to the private API container. Only ports 80 and 443 were public; SSH was limited to the deploying machine's IP.

Browser role switching remains a **demo identity** control. The former shared login did not enforce individual identity.

## Post-deletion check

```bash
az group exists -n rg-savo-sitescout-demo -o tsv
```

The expected result is `false`. The Docker volumes on the deleted VM were not backed up as part of retirement. The old shared demo password was removed from current documentation but may remain in earlier Git commits; do not reuse it.
