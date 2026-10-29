# Deploy on your network

The Docker image builds React and serves it with the Python API on port 8765.
The destination needs Docker Engine with Compose, or Docker Desktop configured
for Linux containers. It needs outbound internet access to download images and
packages during the build and to fetch market data at runtime. Python and Node
do not need to be installed on the destination.

## First deployment

1. Clone or copy this repository to the destination machine.
2. Copy `.env.example` to `.env` (PowerShell: `Copy-Item .env.example .env`).
   If `.env` already exists, add the deployment settings without overwriting your key.
3. Set `FINANCIAL_MODELING_PREP_API_KEY` and replace the example
   `STOCK_PIPELINE_ALLOWED_ORIGINS` with the exact URLs you will use in a browser,
   such as `http://192.168.1.50:8765,http://stock-server:8765`.
   Use a reserved DHCP address or stable hostname. Origins have no path and
   include the scheme and port. Localhost development origins remain allowed.
4. From the repository root, run:

   ```sh
   docker compose up -d --build
   docker compose logs --tail=100
   ```

5. Allow inbound TCP port 8765 from your trusted LAN in the host firewall.
   Open `http://<server-ip>:8765` from another machine. Test company research
   and start a small screening workflow to verify browser POST requests work.

The API key is supplied at runtime; `.env` and local caches are excluded from
the image build. Do not publish your `.env`. The default port binding listens
on every host interface; optionally set `STOCK_PIPELINE_BIND_ADDRESS` to the
server's LAN IP. There is no application login: restrict access to your trusted
network and do not forward this port from your router. Origin filtering is not
authentication. For access beyond that network, add authentication and HTTPS
at a reverse proxy or use an authenticated private network.

Compose restarts the service unless explicitly stopped, provided Docker starts
on boot. One Python worker is intentional: workflow state and rate limiting
are process-local. All clients share the server's single workflow execution slot.

## Data and backups

Compose keeps `data/` (including the market-data cache) and `output/` (including
saved workflow history) in named Docker volumes. These start empty on first
deployment; the development machine's cache and history are not copied into
the image. Back up both volumes before upgrades if you need to retain them.
Stop the service while taking a consistent filesystem backup of the cache.

Watchlists, notes and valuation models remain in browser storage. They do not
move with the server or sync between browsers. A different hostname or port is
a different browser origin; export anything you need before changing addresses.
Active workflows and in-memory snapshots do not survive a server restart;
completed archived runs do.

## Updates and operation

After pulling or copying updated source, run:

```sh
docker compose up -d --build
```

For a change to `.env` alone, run `docker compose up -d` to recreate the service
with the new settings. `docker compose restart` alone does not apply those settings.

```sh
docker compose ps
docker compose logs -f --tail=100
docker compose stop
docker compose start
```

`docker compose down` removes the container but retains named volumes.
`docker compose down -v` deletes the cache and saved history as well.

To ship a prebuilt image to a machine without rebuilding, build it on a machine
with the same target CPU architecture, then run:

```sh
docker save -o stock-pipeline-image.tar stock-pipeline:local
```

Copy the tar file, `compose.yaml` and `.env.example` to the destination. Configure
`.env`, run `docker load -i stock-pipeline-image.tar`, then
`docker compose up -d --no-build`. Market-data requests still need internet access.
