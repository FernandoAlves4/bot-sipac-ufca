# 🎯 Cheatsheet — Bot SIPAC UFCA

## Comandos do sistema (systemd)

| Comando | O que faz |
|---|---|
| `sudo systemctl status bot-sipac` | Ver se está rodando |
| `sudo systemctl restart bot-sipac` | **Reiniciar após editar bot.py** |
| `sudo systemctl stop bot-sipac` | Parar o bot |
| `sudo systemctl start bot-sipac` | Iniciar o bot |
| `sudo journalctl -u bot-sipac -n 50` | Ver últimos logs |
| `cat ~/bot_sipac/bot.log` | Ver log do arquivo |

## Atualizar a base de conhecimento

Sempre que a Wiki UFCA mudar:

```bash
cd ~/bot_sipac
source venv/bin/activate
python3 leitor_site.py      # Atualiza faq_sipac.txt
python3 leitor_wiki.py      # Atualiza outras_paginas.txt
sudo systemctl restart bot-sipac

## Comandos do bot no Telegram

- `/start` — boas-vindas
- `/ajuda` — exemplos de perguntas
- `/status` — painel de estatísticas
- `/historico` — ver o que você já perguntou
- `/limpar` — apagar seu histórico de conversa
