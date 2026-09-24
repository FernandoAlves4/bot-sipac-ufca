# 🤖 Bot SIPAC UFCA

Bot do Telegram que responde dúvidas sobre a UFCA com base em **fontes oficiais** (Wiki UFCA), usando **RAG + IA**.

## 📋 Sobre

Este bot foi criado para ajudar a comunidade acadêmica da UFCA a encontrar informações sobre sistemas, redes e serviços da universidade.

**Como funciona:**
1. O usuário manda uma pergunta no Telegram
2. O bot busca a informação em uma base de conhecimento (Wiki UFCA)
3. A IA (Groq) gera uma resposta natural com base no conteúdo oficial
4. Se não encontrar, indica o link oficial ou o Atende UFCA

## ✨ Funcionalidades

- **Busca híbrida**: RAG (embeddings) + fuzz (similaridade) + sinônimos
- **IA contextual**: usa histórico de conversa para entender follow-ups
- **Respostas formatadas**: HTML no Telegram (negrito, listas, links)
- **Histórico persistente**: sobrevive a reinicializações
- **Aprendizado automático**: atualização semanal da base
- **Feedback**: botões 👍/👎 em cada resposta
- **Comandos úteis**: `/ajuda`, `/exemplos`, `/status`, `/historico`, `/limpar`, `/feedback`

## 📚 Base de conhecimento

| Fonte | Conteúdo | Blocos |
|---|---|---|
| **FAQ SIPAC** | 17 perguntas do FAQ oficial | 17 |
| **Wiki UFCA** | 22 tutoriais (rede, Office, SIGAA, etc) | 22 |
| **Info extra** | Conteúdo manual (DTI, sistemas) | 11 |
| **Total** | | **50** |

## 🤖 Tecnologias

- **Python 3.12**
- **python-telegram-bot** — interface do Telegram
- **sentence-transformers** — embeddings (RAG)
- **rapidfuzz** — busca fuzzy
- **Groq API** (modelo `openai/gpt-oss-120b`) — IA
- **BeautifulSoup** + **requests** — scraping da Wiki
- **GraphQL** — listagem de páginas da Wiki
- **systemd** — serviço 24/7
- **cron** — atualização semanal

## 🚀 Como rodar localmente

```bash
git clone https://github.com/FernandoAlves4/bot-sipac-ufca.git
cd bot-sipac-ufca
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Criar .env com os tokens
nano .env
# TELEGRAM_TOKEN=seu_token
# GROQ_API_KEY=sua_chave

# Gerar base de conhecimento
python3 leitor_site.py
python3 leitor_wiki.py
python3 gerar_embeddings.py

# Rodar o bot
python3 bot.py

🖥️ Deploy em produção
O bot roda na Oracle Cloud Free Tier (VM x86, 1GB RAM, 2 CPUs).

Serviços configurados:

systemd: bot-sipac.service (auto-start, auto-restart)

cron: atualização semanal (domingo 3h)

swap: 6GB (otimização pra 1GB RAM)

Veja o cheatsheet.md para os comandos de gerenciamento.

📊 Status do projeto
Componente	Status
Bot funcional	✅
Base de conhecimento	✅ (50 blocos)
RAG + IA	✅
Histórico	✅
Deploy 24/7	✅
Atualização automática	✅
Documentação	✅
🎯 Roadmap
Feito
☑ Bot básico
☑ Base de conhecimento (FAQ + Wiki)
☑ Busca híbrida (RAG + fuzz)
☑ IA contextual
☑ Histórico persistente
☑ HTML formatado
☑ Deploy em VM
☑ Atualização automática
Futuro
□ Migrar pra VM ARM (mais RAM)
□ Adicionar mais sistemas (SEI, Moodle)
□ Dashboard de métricas
□ Suporte a múltiplos idiomas
🤝 Contribuindo
Sugestões são bem-vindas! Use o comando /feedback no bot ou abra uma issue no GitHub.

📄 Licença
Uso interno da UFCA.

👤 Autor
Fernando Alves (@FernandoAlves4)

⚠️ Importante: o bot não inventa respostas. Se não encontrar na base oficial, indica o link ou o Atende UFCA.
