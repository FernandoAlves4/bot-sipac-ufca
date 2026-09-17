#!/bin/bash

# Script de atualização automática da base do Bot SIPAC UFCA
# Roda os leitores e reinicia o systemd

# Entra na pasta do projeto
cd /home/fernando/bot_sipac

# Data pra log
DATA=$(date "+%Y-%m-%d %H:%M:%S")

echo ""
echo "==============================================="
echo "[$DATA] Iniciando atualização da base..."
echo "==============================================="

# Ativa o venv
source venv/bin/activate

# 1. Atualizar a FAQ do SIPAC
echo "[1/3] Atualizando faq_sipac.txt..."
python3 leitor_site.py

# 2. Atualizar as outras páginas da Wiki
echo ""
echo "[1/4] Atualizando faq_sipac.txt..."
python3 leitor_wiki.py

# 3. Regenerar embeddings (base pode ter mudado)
echo ""
echo "[2/4] Atualizando outras_paginas.txt..."
python3 gerar_embeddings.py

# 4. Reiniciar o bot pra carregar a base nova
echo ""
echo "[4/4] Reiniciando o bot..."
sudo systemctl restart bot-sipac
