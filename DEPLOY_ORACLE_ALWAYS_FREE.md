# Oracle Cloud Always Free deployment

Verified against Oracle's current Free Tier documentation in August 2026.

## Why this target

The current architecture needs a real 24/7 Linux VM because it uses FastAPI, SQLite persistence, background discovery jobs and Docker. A tunnel alone cannot keep the app alive when the office PC is off.

Oracle documents Always Free compute in the tenancy home region, including VM.Standard.E2.1.Micro and Ampere A1 Flex capacity subject to regional availability/capacity. Always stay inside resources marked **Always Free eligible** in the Oracle Console.

## Recommended VM for this project

For a lightweight zero-cost test deployment:

- Ubuntu 24.04 LTS (or 22.04 LTS)
- Ampere A1 Flex if Always Free capacity is available
- Keep CPU/RAM within the Oracle Console's Always Free limits
- 50 GB boot volume is sufficient for the first test
- Do not provision optional paid resources

The application does not require inbound port 8000. Cloudflare Tunnel connects outbound from the VM.

## 1. Create the VM

In OCI Console create a Compute Instance in your home region and choose only a shape/resource explicitly marked Always Free eligible. Add your SSH public key. Do not paste private keys into GitHub or ChatGPT.

If Oracle reports out-of-host-capacity, try another availability domain or later; do not switch to a paid shape just to proceed.

## 2. Connect over SSH

Typical Ubuntu login:

```bash
ssh ubuntu@YOUR_VM_PUBLIC_IP
```

## 3. Clone the repository

```bash
git clone https://github.com/elsamman78-tech/Tender_intelligence.git
cd Tender_intelligence
```

## 4. Install Docker

```bash
sudo bash scripts/bootstrap_ubuntu.sh
```

Log out and back in once if the script says Docker group membership changed.

## 5. Start Tender Intelligence

```bash
cd Tender_intelligence
cp .env.cloud.example .env
chmod +x scripts/*.sh
./scripts/cloud_start.sh
./scripts/verify_deployment.sh
```

The app should respond locally at `http://127.0.0.1:8000/api/v1/health`.

## 6. Add Cloudflare Tunnel

Create a Cloudflare Tunnel from the Cloudflare dashboard. Store its token only in the VM's `.env` file:

```env
CLOUDFLARE_TUNNEL_TOKEN=REPLACE_ON_SERVER_ONLY
```

Then:

```bash
./scripts/cloud_start_with_cloudflare.sh
```

In the Tunnel public-hostname configuration, route the hostname to:

```text
http://tender-intelligence:8000
```

Cloudflare Tunnel is available on all Cloudflare plans. Protect the hostname with Cloudflare Access before normal use.

## 7. Security acceptance

- `.env` remains untracked.
- No API keys/tokens/passwords are committed.
- Port 8000 is bound only to `127.0.0.1` on the VM.
- Cloudflare Access is enabled for the public hostname.
- The VM runs only Always Free eligible OCI resources.

## 8. Update later

```bash
cd Tender_intelligence
./scripts/update_from_github.sh
./scripts/verify_deployment.sh
```

## 9. Backup

```bash
./scripts/backup.sh
```

Current backups are local to the VM. Off-machine encrypted backup remains a later production task.
