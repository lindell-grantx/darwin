# Darwin v2 deployment

The Python supervisor runs on a GCE VM. The Hono server runs locally for dev or on a separate process for prod (TBD in Pass 2 hardening).

## Initial provisioning

```bash
export DARWIN_GCP_SECRET_PROJECT=your-project
bash infra/gce/setup.sh
```

This:
1. Creates a `darwin-supervisor` e2-medium VM in `us-central1-a`
2. Adds the Google Cloud SDK apt repo and installs `google-cloud-cli`, Python 3.11 (Debian 12 default), and `git`
3. Clones the repo and sets up the venv
4. Writes `/etc/darwin.env` with `DARWIN_GCP_SECRET_PROJECT` and `ANTHROPIC_VERTEX_PROJECT_ID` (both default to the same project)
5. Creates `/var/log/darwin/` and chowns it to `lcume` so the systemd unit's log path exists before first start

### Project IDs and Vertex AI

`/etc/darwin.env` sets `ANTHROPIC_VERTEX_PROJECT_ID` to the same project as Secret Manager by default. Vertex AI must be enabled on that project for the supervisor's Anthropic-via-Vertex calls to work. If you need Vertex AI in a different project than secrets, edit `/etc/darwin.env` post-provision and restart the systemd unit.

### Secret resolution

`/etc/darwin.env` deliberately omits Mongo URI and Voyage API key. The supervisor (`scripts/run_all.py`) resolves both at startup by shelling out to `gcloud secrets versions access latest` for `darwin-mongodb-uri` and `darwin-voyage-key` (see `src/darwin/lib/secrets.py`). This keeps plaintext credentials off the VM disk and is why `setup.sh` installs `google-cloud-cli` (Debian 12 does not ship it by default).

The VM's service account (default: `darwin-supervisor@${DARWIN_GCP_SECRET_PROJECT}.iam.gserviceaccount.com`) MUST be granted `roles/secretmanager.secretAccessor` on both secrets, otherwise the supervisor will crash at boot with `MongoDB URI not set`.

### Install the systemd unit

After provisioning:

```bash
gcloud compute scp infra/systemd/darwin-supervisor.service darwin-supervisor:/tmp/ --zone=us-central1-a
gcloud compute ssh darwin-supervisor --zone=us-central1-a --command="
  sudo mv /tmp/darwin-supervisor.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now darwin-supervisor
"
```

(`/var/log/darwin/` is already created by `setup.sh`; no need to re-mkdir here.)

## Operations

- **Status**: `sudo systemctl status darwin-supervisor`
- **Logs**: `tail -f /var/log/darwin/supervisor.log` (or `journalctl -u darwin-supervisor -f`)
- **Restart**: `sudo systemctl restart darwin-supervisor`
- **Stop**: `sudo systemctl stop darwin-supervisor`

## Recompute Nash (cron)

Add to user's crontab:

```cron
*/15 * * * * cd /home/lcume/darwin && /home/lcume/darwin/.venv/bin/python scripts/recompute_nash.py >> /var/log/darwin/recompute_nash.log 2>&1
```

Adjust frequency for production. MVP runs every 15 min as a cheap cadence; Pass 2 ties this to the K=10 generation cadence.
