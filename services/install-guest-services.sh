#!/bin/bash

cp sshd.service /etc/systemd/system/
cp blyss-server-nginx.conf /etc/nginx/sites-available/enclave.blyss.dev
ln -s /etc/nginx/sites-available/enclave.blyss.dev /etc/nginx/sites-enabled/

cp blyss-nvidia-persistenced.service /etc/systemd/system/
cp blyss-server.service /etc/systemd/system/

systemctl daemon-reload

systemctl enable blyss-nvidia-persistenced.service
systemctl enable blyss-server.service
systemctl enable nginx.service