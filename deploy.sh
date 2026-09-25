#!/bin/bash
# Script de deploy: PC → GitHub → VM
# Uso: ./deploy.sh "mensagem do commit"

set -e  # Para se der erro

MSG="${1:-Atualização}"

echo "📤 [1/3] Commit + push no PC..."
cd ~/bot_sipac
git add .
git commit -m "$MSG" || echo "Nada pra commitar"
git push

echo ""
echo "🚀 [2/3] Atualizando a VM..."
ssh oci-danilo "cd ~/bot-sipac-ufca && git pull"

echo ""
echo "🔄 [3/3] Reiniciando o bot..."
ssh oci-danilo "sudo systemctl restart bot-sipac && sleep 5 && sudo systemctl status bot-sipac | head -3"

echo ""
echo "✅ Deploy concluído!"
