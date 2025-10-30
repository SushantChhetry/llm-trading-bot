#!/bin/bash
# Configure system log rotation for application logs

echo "Configuring logrotate for trading bot..."

sudo tee /etc/logrotate.d/trading-bot << 'EOF'
/opt/trading-bot/data/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    copytruncate
    dateext
    dateformat -%Y%m%d
    create 0644 $USER $USER
    sharedscripts
    postrotate
        # Send HUP signal to reload log files
        systemctl reload trading-bot.service >/dev/null 2>&1 || true
        systemctl reload trading-api.service >/dev/null 2>&1 || true
    endscript
}

# JSON logs - keep longer for analysis
/opt/trading-bot/data/logs/*.json.log {
    weekly
    rotate 12
    compress
    delaycompress
    notifempty
    missingok
    copytruncate
    dateext
    dateformat -%Y%m%d
    create 0644 $USER $USER
}
EOF

echo "✅ Logrotate configured successfully"
echo "Testing logrotate configuration..."
sudo logrotate -d /etc/logrotate.d/trading-bot
