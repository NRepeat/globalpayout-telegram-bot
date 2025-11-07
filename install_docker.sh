#!/bin/bash

# Install Dependencies
sudo DEBIAN_FRONTEND=noninteractive apt update
sudo DEBIAN_FRONTEND=noninteractive apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg

if ! [ -x "$(command -v docker)" ]; then
  echo "Installing Docker..."

  # Add Docker's official GPG key
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  # Add the repository to Apt sources
  echo \
    "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo DEBIAN_FRONTEND=noninteractive apt update
  sudo DEBIAN_FRONTEND=noninteractive apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  sudo systemctl start docker
  sudo systemctl enable docker
  sudo docker --version
  sudo docker run hello-world
  echo "Docker has been installed successfully."
fi

if ! systemctl is-active --quiet docker; then
  echo 'Error: Docker is not running.' >&2
  exit 1
fi

if ! [ -x "$(command -v docker compose)" ]; then
  echo "Docker Compose is now included with Docker. You can use 'docker compose' instead of 'docker-compose'."
  docker compose version
else
  echo "Docker Compose is already installed."
fi