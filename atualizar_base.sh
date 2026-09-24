#!/bin/bash
cd /home/nando/bot-sipac-ufca
DATA=$(date "+%Y-%m-%d %H:%M:%S")
echo "[$DATA] Iniciando atualização..."

source venv/bin/activate
python3 leitor_site.py
python3 leitor_wiki.py
python3 gerar_embeddings.py

echo "[$DATA] Reiniciando bot..."
sudo systemctl restart bot-sipac

echo "[$DATA] Atualização concluída!"
