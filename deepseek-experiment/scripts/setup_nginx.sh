#!/bin/bash
# Setup Nginx as reverse proxy

sudo tee /etc/nginx/sites-available/trading-bot << 'EOF'
server {
    listen 80;
    server_name _;

    # API backend
    location /api/ {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Frontend (if serving built React app)
    location / {
        root /opt/trading-bot/web-dashboard/dist;
        try_files $uri $uri/ /index.html;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/trading-bot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl restart nginx

echo "✅ Nginx configured!"
