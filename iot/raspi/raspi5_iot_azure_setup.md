# Azure IoT Edge Setup Guide for Raspberry Pi 5

This guide documents the complete setup process for configuring a Raspberry Pi 5 as an Azure IoT Edge device connected to an Azure-hosted backend.

## Prerequisites

- Raspberry Pi 5 with fresh Raspberry Pi OS (Debian 12 bookworm)
- SSH access to the device
- Azure subscription with appropriate permissions
- Internet connectivity on the Raspberry Pi

## System Information

After following this guide, you'll have:
- **Device**: Raspberry Pi 5 (ARM64/aarch64)
- **OS**: Debian GNU/Linux 12 (bookworm) 
- **Kernel**: 6.12.25+rpt-rpi-2712
- **Memory**: 8GB RAM
- **Storage**: 64GB with 50GB+ available

## Step 1: Connect and Verify System

SSH into your Raspberry Pi and check the system information:

```bash
# Connect via SSH
ssh pi@<your-pi-ip-address>

# Verify system information
uname -a
cat /etc/os-release
df -h
free -h
```

Expected output should show:
- Architecture: aarch64
- OS: Debian 12 (bookworm)
- Sufficient disk space (50GB+ available)
- Adequate RAM (4GB+ recommended)

## Step 2: Update System and Install Prerequisites

Update the package lists and install essential tools:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y \
    curl \
    wget \
    gnupg \
    lsb-release \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    git \
    htop \
    nano \
    vim \
    unzip \
    jq
```

## Step 3: Install Docker Engine

Install Docker CE for ARM64 architecture:

```bash
# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository for Debian bookworm ARM64
echo "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian bookworm stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index and install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Verify Docker installation
sudo docker run hello-world
```

## Step 4: Install Azure CLI

Install Azure CLI for managing Azure resources:

```bash
# Download and install Microsoft GPG key
curl -sLS https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | sudo tee /etc/apt/keyrings/microsoft.gpg > /dev/null
sudo chmod go+r /etc/apt/keyrings/microsoft.gpg

# Add Azure CLI repository for Debian bookworm
echo "deb [arch=arm64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/azure-cli/ bookworm main" | sudo tee /etc/apt/sources.list.d/azure-cli.list

# Update package index and install Azure CLI
sudo apt update
sudo apt install -y azure-cli

# Verify installation
az version
```

## Step 5: Install Azure IoT Edge Runtime

Install the Azure IoT Edge runtime and identity service:

```bash
# Download and install Microsoft package signing key
wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb

# Update package index and install IoT Edge
sudo apt update
sudo apt install -y aziot-edge

# Install IoT Identity Service
sudo apt install -y aziot-identity-service

# Verify installation (service will be inactive until configured)
sudo iotedge version
```

## Step 6: Create Azure Resources (if needed)

If you don't have Azure IoT Hub resources, create them:

```bash
# Login to Azure
az login

# Create resource group (replace with your preferred name and location)
az group create --name msfthackathon2025 --location eastus

# Create IoT Hub (replace with your preferred hub name)
az iot hub create --name msfthack2025IoTHub --resource-group msfthackathon2025 --sku F1

# Create IoT Edge device identity (replace with your preferred device name)
az iot hub device-identity create --hub-name msfthack2025IoTHub --device-id railroadEdgeDevice --edge-enabled

# Get the connection string
az iot hub device-identity connection-string show --hub-name msfthack2025IoTHub --device-id railroadEdgeDevice
```

Save the connection string output for the next step.

## Step 7: Configure IoT Edge Device

Configure the IoT Edge device with your connection string:

```bash
# Edit the IoT Edge configuration file
sudo nano /etc/aziot/config.toml
```

Add the following configuration (replace with your actual connection string):

```toml
# Azure IoT Edge Configuration

[provisioning]
source = "manual"
connection_string = "HostName=your-iot-hub.azure-devices.net;DeviceId=your-device-id;SharedAccessKey=your-key"

[agent]
name = "edgeAgent"
type = "docker"

[agent.config]
image = "mcr.microsoft.com/azureiotedge-agent:1.4"

[connect]
workload_uri = "unix:///var/run/iotedge/workload.sock"
management_uri = "unix:///var/run/iotedge/mgmt.sock"

[listen]
workload_uri = "fd://aziot-edged.workload.socket"
management_uri = "fd://aziot-edged.mgmt.socket"

[moby_runtime]
uri = "unix:///var/run/docker.sock"
network = "azure-iot-edge"
```

Apply the configuration:

```bash
# Apply the configuration
sudo iotedge config apply

# Check the status
sudo systemctl status aziot-edged

# Verify edge agent is running
sudo iotedge list
```

## Step 8: Install Additional IoT Development Tools

Install Python development environment and tools:

```bash
# Install Python development tools
sudo apt install -y python3-full python3-pip python3-venv python3-dev

# Install system Python packages
sudo apt install -y python3-azure python3-requests python3-paho-mqtt

# Create virtual environment for Azure IoT packages
python3 -m venv ~/iot-venv
source ~/iot-venv/bin/activate

# Install Azure IoT packages in virtual environment
pip install azure-iot-device

# Deactivate virtual environment
deactivate

# Create helper script to activate IoT environment
echo '#!/bin/bash
source ~/iot-venv/bin/activate
echo "Azure IoT Python environment activated"
echo "Available packages: azure-iot-device"' > ~/activate-iot-env.sh

chmod +x ~/activate-iot-env.sh
```

Install Node.js and monitoring tools:

```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# Install system monitoring tools
sudo apt install -y iotop iftop net-tools tree

# Install development tools
sudo apt install -y build-essential cmake
```

## Step 9: Verify Installation

Run comprehensive verification tests:

```bash
# Check IoT Edge status and configuration
sudo iotedge check

# List running edge modules
sudo iotedge list

# Check component versions
docker --version
az --version
node --version

# Test Python IoT SDK
source ~/iot-venv/bin/activate
python3 -c "import azure.iot.device; print('Azure IoT Device SDK: OK')"
deactivate

# Check Azure connectivity
az iot hub device-identity show --hub-name msfthack2025IoTHub --device-id railroadEdgeDevice --query "connectionState"
```

## Verification Results

A successful setup should show:
- `sudo iotedge check`: Most checks passing (warnings about DNS, logs, and storage are normal)
- `sudo iotedge list`: Shows edgeAgent module running
- Azure connectivity confirmed
- All development tools accessible

## Daily Operations

### Key Commands

```bash
# Check edge status
sudo iotedge list
sudo iotedge check

# View module logs
sudo iotedge logs edgeAgent

# Activate Python IoT environment
source ~/iot-venv/bin/activate
# or
~/activate-iot-env.sh

# Monitor system resources
htop
df -h
free -h

# Check Docker containers
docker ps
```

### Configuration Files

- **IoT Edge config**: `/etc/aziot/config.toml`
- **Python IoT environment**: `~/iot-venv/`
- **Docker daemon**: `/etc/docker/daemon.json` (if customization needed)

## Next Steps

Your Raspberry Pi 5 is now ready for:

1. **Deploying Edge Modules**: Use Azure Portal or CLI to deploy custom modules
2. **IoT Application Development**: Develop Python or Node.js applications using the installed SDKs
3. **Sensor Integration**: Connect sensors and actuators to your edge device
4. **Custom Business Logic**: Implement edge computing scenarios

## Troubleshooting

### Common Issues

1. **Permission denied with Docker**: Logout and login again after adding user to docker group
2. **IoT Edge not starting**: Check config.toml syntax and connection string
3. **Module deployment failures**: Verify network connectivity and Docker functionality
4. **Python package conflicts**: Use the virtual environment (`~/iot-venv/`)

### Useful Log Locations

- IoT Edge logs: `sudo iotedge logs edgeAgent`
- System logs: `sudo journalctl -u aziot-edged`
- Docker logs: `docker logs <container-name>`

## Resource Information

- **Device ID**: railroadEdgeDevice
- **IoT Hub**: msfthack2025IoTHub  
- **Resource Group**: msfthackathon2025
- **Architecture**: ARM64 (aarch64)
- **OS**: Debian 12 (bookworm)

---

**Setup completed successfully!** 🎉

Your Raspberry Pi 5 is now a fully functional Azure IoT Edge device ready for production IoT workloads.