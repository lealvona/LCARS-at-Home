# Docker Installation (Linux Mint Xia / Windows / macOS)

This project can be run on:

- **Linux Mint Xia (recommended target)** using **Docker Engine + Compose plugin**.
- **Windows** using **Docker Desktop** (WSL 2 recommended).
- **macOS** using **Docker Desktop**.

This doc intentionally points to Docker’s official instructions and includes a working, copy/paste installation path for Mint (Ubuntu-based).

## Linux Mint Xia (recommended)

Docker’s Ubuntu install guide notes that Ubuntu derivatives (like Mint) are not officially supported, but the Ubuntu repository method commonly works.

### Option A (recommended): Install Docker Engine from Docker’s apt repository

Based on Docker’s official Ubuntu instructions:

```bash
# 0) Remove conflicting packages (safe even if none installed)
sudo apt remove -y \
  docker.io docker-compose docker-compose-v2 docker-doc podman-docker \
  containerd runc || true

# 1) Set up Docker's apt repository
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update

# 2) Install Docker Engine + Compose plugin
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 3) Verify
sudo docker run hello-world
docker compose version
```

### Post-install (optional): Run docker without sudo

From Docker’s Linux post-install docs:

```bash
sudo groupadd docker || true
sudo usermod -aG docker $USER
newgrp docker

docker run hello-world
```

Note: Membership in the `docker` group effectively grants root-level privileges.

### Option B (dev/testing only): Docker convenience script

Docker’s convenience script is useful for quick dev machines but is not recommended for production:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

## Windows

Use Docker Desktop (official):

- <https://docs.docker.com/desktop/install/windows-install/>

Notes:

- WSL 2 is the typical backend and requires virtualization enabled.
- Docker Desktop has license terms for larger enterprises.

## macOS

Use Docker Desktop (official):

- <https://docs.docker.com/desktop/install/mac-install/>

Notes:

- Docker Desktop supports the current and two previous major macOS releases.

## Compose

This project uses the modern Compose v2 plugin (`docker compose ...`), not legacy `docker-compose`.

Official Compose plugin docs:

- <https://docs.docker.com/compose/install/linux/>
