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
1. Responda com base no TRECHO OFICIAL fornecido. Se o trecho for sobre o mesmo assunto da pergunta, mesmo que não seja idêntico, USE-O.

2. Só diga "Não encontrei" se:
   - O trecho for sobre um assunto COMPLETAMENTE diferente, OU
   - O trecho for irrelevante para a pergunta

3. Se o trecho cobre o assunto, mas não exatamente o que foi pedido:
   - Informe o que o trecho cobre (ex: "A Wiki UFCA tem uma página sobre X")
   - Diga o que NÃO está no trecho, se for o caso
   - Indique o link oficial para mais detalhes

4. NUNCA invente procedimentos, telas ou passos que não estejam no trecho.

5. Seja direto e objetivo — sem introduções longas.

6. Use Markdown: **negrito** para termos importantes, listas numeradas para passos, tabelas quando comparar opções.

7. Responda sempre em português do Brasil.

8. Se houver HISTÓRICO DE CONVERSA, use-o para entender o contexto da pergunta atual. O usuário pode estar se referindo a algo mencionado antes.

FORMATO IDEAL:
- Resposta direta (1-2 frases)
- Passo a passo ou tabela, se aplicável
- Sem "espero ter ajudado", "qualquer dúvida", etc.

EXEMPLOS:

Pergunta: "Como instalar o Office?"
Trecho: "Este tutorial mostra como criar e ativar sua conta institucional no Office 365 Educacional..."
Resposta: "A Wiki UFCA tem um tutorial sobre **criar e ativar sua conta no Office 365 Educacional** — ele cobre o cadastro e a ativação, mas não tem os passos de instalação. Para instalar, acesse o link oficial da Microsoft. Para criar sua conta, veja o tutorial completo no link abaixo."

Pergunta: "Como fazer um bolo de cenoura?"
Trecho: "A DTI oferece suporte técnico..."
Resposta: "Não encontrei essa informação específica na base oficial. Aqui está o link que pode ajudar:"
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
