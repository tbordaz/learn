#!/bin/bash
sudo dnf update -y
sudo dnf install -y amazon-ssm-agent bind-utils

sudo systemctl restart amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent
