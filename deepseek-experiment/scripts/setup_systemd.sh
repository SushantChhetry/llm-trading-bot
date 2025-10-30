#!/bin/bash
# Setup systemd services for auto-restart

# Trading bot service
sudo tee /etc/systemd/system/trading-bot.service << EOF
[Unit]
Description=LLM Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/trading-bot
Environment="PATH=/opt/trading-bot/venv/bin"
EnvironmentFile=/opt/trading-bot/.env
ExecStart=/opt/trading-bot/venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# API server service
sudo tee /etc/systemd/system/trading-api.service << EOF
[Unit]
Description=Trading Bot API Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/trading-bot
Environment="PATH=/opt/trading-bot/venv/bin"
EnvironmentFile=/opt/trading-bot/.env
ExecStart=/opt/trading-bot/venv/bin/python web-dashboard/api_server_supabase.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable trading-bot.service
sudo systemctl enable trading-api.service

echo "✅ Systemd services configured!"
