# 🤖 Bot SIPAC UFCA

Bot do Telegram que responde dúvidas sobre a UFCA com base em fontes oficiais (Wiki UFCA), usando RAG + IA.

## O que ele faz

- Responde perguntas sobre SIPAC, Wi-Fi, Office 365, SIGAA, impressão, assinatura digital e mais
- Busca híbrida (embeddings + fuzz + sinônimos)
- IA contextual (Groq - gpt-oss-120b)
- Histórico persistente de conversa
- Atualização automática semanal da base

## Comandos do bot

- `/start` — boas-vindas
- `/ajuda` — exemplos de perguntas
- `/status` — estatísticas
- `/historico` — ver suas últimas perguntas
- `/limpar` — apagar histórico

## Tecnologias

- Python 3.12
- python-telegram-bot
- sentence-transformers (RAG)
- rapidfuzz (busca fuzzy)
- Groq API (IA)
- BeautifulSoup (scraping)
- GraphQL (Wiki UFCA)
- systemd + cron (produção)

## Como rodar localmente

```bash
git clone https://github.com/FernandoAlves4/bot-sipac-ufca.git
cd bot-sipac-ufca
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Criar .env com TELEGRAM_TOKEN e GROQ_API_KEY
python3 leitor_site.py       # Gera faq_sipac.txt
python3 leitor_wiki.py       # Gera outras_paginas.txt
python3 gerar_embeddings.py  # Gera embeddings.pkl
python3 bot.py
