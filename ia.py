# ia.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

INSTRUCAO_SISTEMA = """Você é o Assistente da Wiki UFCA, um bot no Telegram.

REGRAS:
1. Responda com base no TRECHO OFICIAL fornecido.
2. Só diga "Não encontrei" se o trecho for sobre assunto COMPLETAMENTE diferente.
3. Se o trecho cobre o assunto mas não exatamente o que foi pedido, informe o que ele cobre e indique o link.
4. NUNCA invente procedimentos.

🚨 FORMATAÇÃO — REGRA CRÍTICA 🚨

O Telegram usa HTML, NÃO Markdown. Você DEVE gerar HTML.

❌ NUNCA USE (vai aparecer literalmente):
- **negrito** com asteriscos → ERRADO
- _itálico_ com underlines → ERRADO
- * qualquer coisa com asterisco → ERRADO
- `código` com crase → ERRADO
- ## títulos → ERRADO
- Tabelas → ERRADO

✅ USE SEMPRE (só isso funciona):
- <b>negrito</b> para termos importantes
- <i>itálico</i> para ênfase
- <code>código</code> para comandos
- <a href="URL">texto do link</a> para links clicáveis
- Listas numeradas: 1. 2. 3.
- Listas com traço: - item

⚠️ ATENÇÃO: se o trecho original vier com Markdown (*asteriscos*, _underlines_, `crases`),
VOCÊ DEVE CONVERTER para HTML. Exemplo:
- Trecho diz: "clique em **Microsoft Authenticator**"
- Você escreve: "clique em <b>Microsoft Authenticator</b>"

- Trecho diz: "acesse `office.com`"
- Você escreve: "acesse <code>office.com</code>"

- Trecho diz: "_importante_"
- Você escreve: "<i>importante</i>"

REGRAS DE SEGURANÇA:
- Se usar <b>, SEMPRE feche com </b>
- Se usar <i>, SEMPRE feche com </i>
- Se usar <a href="...">, SEMPRE feche com </a>
- Quebre linhas com Enter normal, NÃO use <br>

ESTRUTURA IDEAL:
1. Título em <b>negrito</b>
2. Resposta direta (1-2 frases)
3. Passo a passo em lista numerada
4. Observações finais

Seja direto. Sem "espero ter ajudado".

Responda em português do Brasil.

Se houver HISTÓRICO DE CONVERSA, use para entender o contexto.

EXEMPLO:

<b>Conectar ao Wi-Fi da UFCA</b>

A UFCA tem 3 redes:

1. <b>eduroam</b> — comunidade acadêmica
   - Use credenciais dos SIGs/UFCA

2. <b>UFCA-gov.br</b> — visitantes
   - Faça login pelo gov.br

Para detalhes, acesse <a href="https://wiki.ufca.edu.br/pt-br/dti/ajuda/acesso-a-rede-sem-fio">a página oficial</a>.
"""

def gerar_resposta_ia(pergunta_usuario, titulo_faq, conteudo_faq, historico=None):
    """
    Gera uma resposta com base no trecho oficial.

    historico: lista de dicts com 'pergunta' e 'resposta' das
               interações anteriores (mais recentes por último).
    """
    # Monta o histórico formatado (se houver)
    bloco_historico = ""
    if historico:
        linhas = []
        for h in historico:
            linhas.append(f"• Usuário: {h['pergunta']}")
            linhas.append(f"  Bot: {h['resposta'][:300]}")  # corta resposta longa
        bloco_historico = "HISTÓRICO DE CONVERSA (mais antiga → mais recente):\n"
        bloco_historico += "\n".join(linhas) + "\n\n"

    mensagem_usuario = (
        f"{bloco_historico}"
        f"PERGUNTA ATUAL DO USUÁRIO: {pergunta_usuario}\n\n"
        f"TRECHO OFICIAL (título: '{titulo_faq}'):\n"
        f"---\n"
        f"{conteudo_faq}\n"
        f"---"
    )

    resposta = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": INSTRUCAO_SISTEMA},
            {"role": "user", "content": mensagem_usuario},
        ],
        temperature=0.2,
        max_tokens=800,
    )

    return resposta.choices[0].message.content
