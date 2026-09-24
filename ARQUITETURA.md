# 🏗️ Arquitetura do Bot SIPAC UFCA

Documentação técnica de como o bot funciona por dentro.

## 📐 Visão geral
┌──────────────────────────────────────────────────┐
│ USUÁRIO (Telegram) │
└──────────────────────────────────────────────────┘
↓
┌──────────────────────────────────────────────────┐
│ BOT (bot.py) │
│ │
│ ┌─────────────────────────────────────────┐ │
│ │ 1. SAUDAÇÃO? │ │
│ │ Se "oi/olá" → responde direto │ │
│ └─────────────────────────────────────────┘ │
│ ↓ │
│ ┌─────────────────────────────────────────┐ │
│ │ 2. DETECÇÃO DE CONTINUAÇÃO │ │
│ │ "E no Linux?" → combina com anterior │ │
│ └─────────────────────────────────────────┘ │
│ ↓ │
│ ┌─────────────────────────────────────────┐ │
│ │ 3. BUSCA HÍBRIDA (5 regras + RAG+fuzz) │ │
│ │ - Regra 1: abrir chamado │ │
│ │ - Regra 2: sistema + problema │ │
│ │ - Regra 3: suporte simples │ │
│ │ - Regra 4: site + suporte │ │
│ │ - Regra 5: palavras de RH │ │
│ │ - RAG: top 5 embeddings │ │
│ │ - Fuzz: reordena + bônus │ │
│ └─────────────────────────────────────────┘ │
│ ↓ │
│ ┌─────────────────────────────────────────┐ │
│ │ 4. IA (ia.py → Groq) │ │
│ │ - Recebe: pergunta + histórico + │ │
│ │ trecho encontrado │ │
│ │ - Gera: resposta em HTML │ │
│ └─────────────────────────────────────────┘ │
│ ↓ │
│ ┌─────────────────────────────────────────┐ │
│ │ 5. HISTÓRICO (historico.json) │ │
│ │ - Salva pergunta + resposta │ │
│ │ - Máx 2 interações por usuário │ │
│ └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
↓
┌──────────────────────────────────────────────────┐
│ RESPOSTA (Telegram) │
└──────────────────────────────────────────────────┘


## 📂 Estrutura de arquivos

| Arquivo | Função |
|---|---|
| `bot.py` | Código principal (handlers, busca, comandos) |
| `ia.py` | Integração com Groq (IA) |
| `gerar_embeddings.py` | Gera embeddings da base |
| `leitor_site.py` | Scraping da FAQ do SIPAC |
| `leitor_wiki.py` | Scraping das outras páginas da Wiki |
| `atualizar_base.sh` | Script de atualização |
| `faq_sipac.txt` | 17 perguntas do FAQ |
| `outras_paginas.txt` | 22 tutoriais da Wiki |
| `info_extra.txt` | 11 blocos manuais |
| `correcoes.txt` | Substituições automáticas |
| `embeddings.pkl` | Embeddings gerados |
| `historico.json` | Histórico dos usuários |
| `feedback.txt` | Votos 👍/👎 |
| `sugestoes.txt` | Sugestões dos usuários |
| `perguntas_nao_encontradas.txt` | Log do que não achou |

## 🔍 Busca híbrida em detalhes

### Etapa 1 — Regras especiais (prioridade máxima)

**5 regras** que pegam casos críticos e retornam **score 999**:

| Regra | Trigger | Bloco retornado |
|---|---|---|
| **1** | `chamado/ticket` + `abrir/criar/preciso` | Suporte da DTI |
| **2** | `sipac/sigaa/sigrh` + `lento/erro/problem` | Suporte da DTI |
| **3** | pergunta curta + `suporte/ajuda/chamado` | Suporte da DTI |
| **4** | `site/url/link` + `atende/suporte/dti` | Suporte da DTI |
| **5** | `contracheque/salario/ferias/sigrh` | SIGRH - Portal do Servidor |

### Etapa 2 — RAG (Retrieval-Augmented Generation)

1. **Embeddings** da pergunta são calculados
2. **Top 5** blocos mais similares são selecionados
3. Filtro: **score ≥ 0.15**

### Etapa 3 — Fuzz (desempate)

Para cada candidato do RAG:
- **Score do título**: `max(token_set, token_sort)` × 0.6
- **Score do conteúdo**: `token_set_ratio` × 0.1
- **Score RAG**: `score_rag × 100 × 0.3`
- **Bônus discriminativos**: palavras raras em comum × 5
- **Bônus cobertura**: `(interseção / total) × 20`
- **Bônus título curto**: ≤ 2 palavras = +25, ≤ 4 = +15, ≤ 7 = +5
- **Penalidade**: conteúdo < 100 chars = -10, < 300 = -5

**Score mínimo final:** 60

## 📊 Otimizações de memória (VM 1GB)

| Otimização | Valor |
|---|---|
| `MAX_HISTORICO` | 2 (era 5) |
| Histórico enviado pra IA | 80 chars (era 300) |
| Swap | 6GB |
| Modelo | `sentence-transformers` (500MB) |

## 🕒 Fluxo de atualização (cron)
Domingo 3h
↓
atualizar_base.sh
↓
┌─────────────────────────────────┐
│ 1. leitor_site.py │
│ → faq_sipac.txt atualizado │
│ │
│ 2. leitor_wiki.py │
│ → outras_paginas.txt │
│ │
│ 3. gerar_embeddings.py │
│ → embeddings.pkl atualizado │
│ │
│ 4. sudo systemctl restart │
│ → bot recarrega a base │
└─────────────────────────────────┘


## 🔒 Segurança

- **`.env`**: contém `TELEGRAM_TOKEN` e `GROQ_API_KEY` (nunca versionar)
- **`.gitignore`**: protege `.env`, `venv/`, logs, backups, embeddings, histórico
- **Sudoers**: `NOPASSWD` apenas pra `systemctl restart bot-sipac`
- **Tokens**: nunca compartilhados em chat/prints

## 🎯 Decisões de design

| Decisão | Por quê |
|---|---|
| **RAG + fuzz** | RAG entende semântica; fuzz desempata com texto exato |
| **Histórico em arquivo** | Sobrevive a restart (era em memória) |
| **Detecção de continuação** | "E no Linux?" precisa do contexto anterior |
| **Regras especiais** | Casos críticos não podem depender do RAG |
| **HTML no Telegram** | Markdown nativo é limitado; HTML é mais confiável |
| **Groq (não OpenAI)** | Gratuito, rápido, modelo aberto |
| **Systemd (não Docker)** | VM pequena; systemd é nativo e leve |
