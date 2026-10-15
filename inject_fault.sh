#!/bin/bash
CONTAINER_NAME="net_router"
echo "--------------------------------------------------"
echo "[+] A INJETAR FALHA (FCAPS - Fault)..."
echo "--------------------------------------------------"
docker exec -i $CONTAINER_NAME ip link set eth1 down
echo "[*] Falha aplicada com sucesso! O enlace principal está inativo."
echo "--------------------------------------------------"