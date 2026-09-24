import os
import json
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import CallbackQueryHandler
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import re
import unicodedata
from rapidfuzz import fuzz
from datetime import datetime

from ia import gerar_resposta_ia


load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")


# --------------------------------------------------
# LER O ARQUIVO DO FAQ
# --------------------------------------------------

with open("faq_sipac.txt", "r", encoding="utf-8") as arquivo:
    faq = arquivo.read()


# --------------------------------------------------
# PREPARAR O TEXTO PARA A BUSCA
# --------------------------------------------------
STOPWORDS = {
    "a", "o", "os", "as", "de", "do", "da", "dos", "das", "um", "uma",
    "uns", "umas", "no", "na", "nos", "nas", "em", "para", "pra", "por",
    "com", "sem", "que", "como", "e", "ou", "se", "ao", "aos", "à", "às",
    "sobre",
    "instalar", "usar", "fazer", "colocar", "criar", "configurar",
    "acessar", "abrir", "clicar", "ver", "preciso", "quero",
    "gostaria", "saber", "faco", "fazer"
}


def limpar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caractere for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    texto = re.sub(r"[^\w\s]", " ", texto)

    palavras = texto.split()
    palavras_importantes = [p for p in palavras if p not in STOPWORDS]

    return " ".join(palavras_importantes)


# --------------------------------------------------
# DETECTAR SAUDAÇÕES
# --------------------------------------------------

SAUDACOES = {
    "oi", "ola", "eae", "opa", "bom dia", "boa tarde",
    "boa noite", "hey", "hello", "e ai"
}


def eh_saudacao(texto):
    texto_limpo = limpar_texto(texto).strip()
    return texto_limpo in SAUDACOES


# --------------------------------------------------
# SEPARAR AS PERGUNTAS DO FAQ
# --------------------------------------------------
ARQUIVO_FAQ = "faq_sipac.txt"
ARQUIVO_CORRECOES = "correcoes.txt"
ARQUIVOS_FONTE = ["faq_sipac.txt", "outras_paginas.txt", "info_extra.txt"]


def carregar_fonte(arquivo):
    """
    Lê UM arquivo de fonte e retorna a lista de blocos.
    Aceita dois formatos:
      - FAQ numerada (ex: "01 - Como consultar...")
      - Tutoriais (ex: "Acesso à rede sem fio")
    """
    if not os.path.exists(arquivo):
        print(f"AVISO: {arquivo} não encontrado, pulando.")
        return []

    with open(arquivo, "r", encoding="utf-8") as f:
        texto = f.read()

    linhas = texto.splitlines()

    blocos = []
    bloco_atual = None

    for linha in linhas:
        linha = linha.strip()

        eh_inicio_numerado = re.match(r"^\d{2}\s*-\s*", linha)

        if eh_inicio_numerado:
            if bloco_atual:
                blocos.append(bloco_atual)
            bloco_atual = {
                "titulo": linha,
                "link": "",
                "conteudo_linhas": [],
                "fonte": arquivo
            }
        elif linha.startswith("="):
            if bloco_atual:
                blocos.append(bloco_atual)
                bloco_atual = None
        elif bloco_atual is None and linha:
            bloco_atual = {
                "titulo": linha,
                "link": "",
                "conteudo_linhas": [],
                "fonte": arquivo
            }
        elif bloco_atual:
            if linha.startswith("http") and not bloco_atual["link"]:
                bloco_atual["link"] = linha
            else:
                bloco_atual["conteudo_linhas"].append(linha)

    if bloco_atual:
        blocos.append(bloco_atual)

    for bloco in blocos:
        bloco["conteudo"] = "\n".join(
            bloco["conteudo_linhas"]
        ).strip()
        del bloco["conteudo_linhas"]

    return blocos


def carregar_correcoes():
    if not os.path.exists(ARQUIVO_CORRECOES):
        return []

    correcoes = []
    with open(ARQUIVO_CORRECOES, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            if "->" in linha:
                errado, certo = linha.split("->", 1)
                correcoes.append((errado.strip(), certo.strip()))

    return correcoes


def aplicar_correcoes(texto, correcoes):
    for errado, certo in correcoes:
        texto = texto.replace(errado, certo)
    return texto


def carregar_faq():
    todos_blocos = []
    correcoes = carregar_correcoes()

    if correcoes:
        print(f"  Correções carregadas: {len(correcoes)}")

    for arquivo in ARQUIVOS_FONTE:
        blocos = carregar_fonte(arquivo)
        print(f"  {arquivo}: {len(blocos)} blocos")

        for bloco in blocos:
            bloco["titulo"] = aplicar_correcoes(bloco["titulo"], correcoes)
            bloco["conteudo"] = aplicar_correcoes(bloco["conteudo"], correcoes)

        todos_blocos.extend(blocos)

    print(f"Base total carregada: {len(todos_blocos)} perguntas/artigos")

    return todos_blocos


perguntas_faq = carregar_faq()


# --------------------------------------------------
# CARREGAR EMBEDDINGS (RAG)
# --------------------------------------------------

ARQUIVO_EMBEDDINGS = "embeddings.pkl"
_modelo_rag = None
_embeddings_base = None


def carregar_embeddings():
    global _modelo_rag, _embeddings_base

    if not os.path.exists(ARQUIVO_EMBEDDINGS):
        print("AVISO: embeddings.pkl não encontrado. Rode gerar_embeddings.py.")
        return False

    try:
        with open(ARQUIVO_EMBEDDINGS, "rb") as f:
            dados = pickle.load(f)

        _modelo_rag = SentenceTransformer(dados["modelo"])
        _embeddings_base = dados["embeddings"]
        print(f"RAG carregado: {len(_embeddings_base)} embeddings")
        return True
    except Exception as e:
        print(f"ERRO ao carregar embeddings: {e}")
        return False


# Pré-carrega o modelo pra primeira mensagem ser rápida
if rag_disponivel:
    print("Pré-carregando modelo de embeddings...", flush=True)
    _modelo_rag.encode(["warmup"])
    print("Modelo pronto!", flush=True)

# --------------------------------------------------
# PROCURAR A PERGUNTA MAIS PARECIDA
# --------------------------------------------------

PALAVRAS_DISCRIMINATIVAS = {
    "restaurante", "patrimonio", "despacho", "tramitacao",
    "movimentacao", "unidade", "externo", "externa", "digito",
    "verificador", "calculadora", "portaria", "configurar",
    "consultar", "adicionar", "cadastrar", "associar", "vincular",
    "usuario", "servidor", "documento", "guia", "modulo",
    "publico", "interno", "atual", "sigiloso", "apensar",
    "assinar", "empenho", "fluxo", "download", "validade",
    "assinatura", "tramita", "gov", "ptres", "programa",
    "trabalho", "cancelar", "bens", "localizados",
    "wifi", "fio", "eduroam", "office", "drive", "vpn",
    "impressao", "impressora", "arquivo", "servidor",
    "softphone", "ramal", "serpro", "monitoria",
    "sigaa", "sigrh", "sigs", "conta", "cadastro",
    "pdf", "tarja", "destacar", "ocultar"
    # RH
    "contracheque", "holerite", "salario", "remuneracao", "pagamento",
    "ferias", "ponto", "sigrh",
}


SINONIMOS = {
    # ==========================================
    # REDE E INTERNET
    # ==========================================
    "wifi": ["rede", "fio", "sem", "wireless"],
    "wi": ["rede", "fio"],
    "fi": ["rede", "fio"],
    "internet": ["rede", "fio", "wifi"],
    "wireless": ["wifi", "rede"],

    # ==========================================
    # IMPRESSÃO
    # ==========================================
    "impressora": ["impressao", "imprimir"],
    "imprimir": ["impressao"],
    "impressao": ["imprimir", "impressora"],

    # ==========================================
    # E-MAIL, OFFICE E COMUNICAÇÃO
    # ==========================================
    "email": ["office", "outlook", "correio", "conta"],
    "outlook": ["office", "email"],
    "teams": ["microsoft", "reuniao", "video"],
    "reuniao": ["teams", "video", "chamada"],
    "video": ["teams", "reuniao"],

    # ==========================================
    # ARMAZENAMENTO EM NUVEM
    # ==========================================
    "drive": ["onedrive", "one"],
    "onedrive": ["drive", "one"],
    "nuvem": ["drive", "onedrive", "armazenamento"],
    "armazenamento": ["drive", "onedrive", "nuvem"],
    "compartilhar": ["drive", "arquivo", "enviar"],

    # ==========================================
    # TELEFONE E RAMAL
    # ==========================================
    "ramal": ["softphone", "telefone"],
    "telefone": ["ramal", "softphone", "chamada"],
    "softphone": ["ramal", "telefone"],

    # ==========================================
    # ASSINATURA DIGITAL
    # ==========================================
    "assinatura": ["assinar", "assinador"],
    "assinador": ["assinar", "assinatura"],
    "assinar": ["assinatura", "assinador"],

    # ==========================================
    # PDF E DOCUMENTOS
    # ==========================================
    "tarja": ["pdf", "destacar", "ocultar"],
    "pdf": ["documento", "arquivo", "anexo"],
    "arquivo": ["documento", "pdf", "anexo", "papel"],
    "anexo": ["arquivo", "documento", "pdf"],
    "papel": ["documento", "arquivo"],
    "digitalizado": ["pdf", "documento"],

    # ==========================================
    # CADASTRO E CONTA
    # ==========================================
    "cadastro": ["conta", "criar"],
    "cadastrar": ["cadastro", "criar", "conta"],
    "conta": ["cadastro", "criar"],

    # ==========================================
    # CONFIGURAÇÃO
    # ==========================================
    "configurar": ["configuracao"],
    "configuracao": ["configurar"],
    "configuracoes": ["configurar", "configuracao"],

    # ==========================================
    # TRAMITAÇÃO E MOVIMENTAÇÃO
    # ==========================================
    "tramitar": ["tramitacao", "movimentacao"],
    "tramitacao": ["tramitar", "movimentacao"],
    "movimentar": ["movimentacao", "tramitar"],
    "movimentacao": ["movimentar", "tramitacao"],
    "mover": ["tramitar", "movimentar", "enviar"],
    "enviar": ["tramitar", "mover", "movimentar"],
    "receber": ["tramitar", "movimentar"],
    "encaminhar": ["tramitar", "mover"],

    # ==========================================
    # DESPACHO
    # ==========================================
    "despachar": ["despacho"],
    "despacho": ["despachar"],

    # ==========================================
    # CANCELAMENTO
    # ==========================================
    "cancelar": ["cancelamento"],
    "cancelamento": ["cancelar"],

    # ==========================================
    # SISTEMAS
    # ==========================================
    "sei": ["sipac", "processo", "eletronico", "protocolo"],
    "protocolo": ["processo", "sipac"],

    # ==========================================
    # SUPORTE E ATENDIMENTO
    # ==========================================
    "suporte": ["dti", "ticket", "chamado", "atende", "ajuda"],
    "ajuda": ["suporte", "dti", "ticket", "chamado"],
    "chamado": ["ticket", "atende", "suporte", "ajuda"],
    "chamados": ["ticket", "atende", "chamado"],
    "ticket": ["chamado", "atende", "suporte", "ajuda"],
    "tickets": ["ticket", "chamado", "atende"],
    "dti": ["suporte", "ticket", "chamado", "atende"],
    "atende": ["ticket", "chamado", "suporte", "dti"],
    "glpi": ["atende", "ticket", "chamado"],

    # ==========================================
    # CHAMADA TELEFÔNICA (≠ chamado de suporte!)
    # ==========================================
    "chamada": ["ligacao", "telefone", "ramal", "telefonica"],
    "ligacao": ["chamada", "telefone", "ramal"],

      # RH / servidor
    "contracheque": ["salario", "pagamento", "holerite", "sigrh", "remuneracao"],
    "holerite": ["contracheque", "salario", "sigrh", "pagamento"],
    "salario": ["contracheque", "holerite", "pagamento", "remuneracao"],
    "remuneracao": ["contracheque", "salario", "holerite"],
    "pagamento": ["contracheque", "salario", "holerite"],
    "ferias": ["sigrh", "descanso", "afastamento"],
    "ponto": ["sigrh", "frequencia", "presenca"],

    # ==========================================
    # ERROS E PROBLEMAS
    # ==========================================
    "erro": ["problema", "falha", "nao funciona", "travando"],
    "problema": ["erro", "falha", "nao funciona"],
    "travando": ["erro", "problema", "nao funciona"],
    "falha": ["erro", "problema"],
    "caiu": ["erro", "problema", "fora"],
    "lento": ["erro", "problema", "travando"],

    # ==========================================
    # LOGIN E SENHA
    # ==========================================
    "login": ["acesso", "entrar", "senha", "credencial"],
    "senha": ["login", "acesso", "credencial", "redefinir"],
    "entrar": ["login", "acessar"],
    "acessar": ["login", "entrar"],
    "redefinir": ["senha", "recuperar", "trocar"],
    "recuperar": ["senha", "redefinir"],
}



def expandir_sinonimos(palavras):
    expandidas = set(palavras)
    for p in palavras:
        if p in SINONIMOS:
            expandidas.update(SINONIMOS[p])
    return expandidas


def buscar_resposta(pergunta_usuario):
    """Busca fallback (sem RAG) — usada se embeddings não estiverem disponíveis."""
    pergunta_limpa = limpar_texto(pergunta_usuario)
    if not pergunta_limpa:
        return None

    palavras_usuario = set(pergunta_limpa.split())
    palavras_usuario_expandidas = expandir_sinonimos(palavras_usuario)

    melhor = None
    melhor_score = 0

    for bloco in perguntas_faq:
        titulo = limpar_texto(bloco["titulo"])
        conteudo = limpar_texto(bloco["conteudo"])
        palavras_titulo = set(titulo.split())

        intersecao = palavras_usuario_expandidas & palavras_titulo
        if not intersecao:
            continue

        score_titulo_set = fuzz.token_set_ratio(pergunta_limpa, titulo)
        score_titulo_sort = fuzz.token_sort_ratio(pergunta_limpa, titulo)
        score_titulo = max(score_titulo_set, score_titulo_sort)
        score_conteudo = fuzz.token_set_ratio(pergunta_limpa, conteudo)

        comuns_raras = intersecao & PALAVRAS_DISCRIMINATIVAS
        bonus = len(comuns_raras) * 5

        if palavras_usuario:
            bonus_cobertura = (len(intersecao) / len(palavras_usuario)) * 20
        else:
            bonus_cobertura = 0

        n_palavras_titulo = len(palavras_titulo)
        if n_palavras_titulo <= 2:
            bonus_titulo_curto = 25
        elif n_palavras_titulo <= 4:
            bonus_titulo_curto = 15
        elif n_palavras_titulo <= 7:
            bonus_titulo_curto = 5
        else:
            bonus_titulo_curto = 0

        tamanho = len(bloco["conteudo"])
        penalidade = 10 if tamanho < 100 else (5 if tamanho < 300 else 0)

        pontuacao = (
            (score_titulo * 0.85)
            + (score_conteudo * 0.15)
            + bonus
            + bonus_cobertura
            + bonus_titulo_curto
            - penalidade
        )

        if pontuacao > melhor_score:
            melhor_score = pontuacao
            melhor = bloco

    if melhor is None or melhor_score < 60:
        return None

    melhor["_score"] = round(melhor_score, 2)
    return melhor


def buscar_resposta_hibrida(pergunta_usuario, top_k_rag=5):
    """
    1. RAG pega os top_k candidatos semanticamente mais próximos.
    2. Fuzz reordena esses candidatos com base em texto exato.
    3. Retorna o melhor.
    """
    pergunta_lower = pergunta_usuario.lower()

    # --------------------------------------------------
    # REGRA 1: "abrir/criar/preciso chamado/ticket" → Atende UFCA
    # --------------------------------------------------
    palavras_chamado = ["chamado", "ticket", "chamados", "tickets"]
    palavras_acao = ["abrir", "criar", "novo", "nova", "fazer", "preciso"]

    if any(p in pergunta_lower for p in palavras_chamado) and \
       any(p in pergunta_lower for p in palavras_acao):
        for bloco in perguntas_faq:
            if "suporte" in bloco["titulo"].lower() or "atend" in bloco["titulo"].lower():
                bloco["_score"] = 999
                return bloco

    # REGRA 2: "problema com SIPAC/SIGAA/etc" → Atende UFCA
    # --------------------------------------------------
    palavras_sistema = ["sipac", "sigaa", "sigrh", "sei", "sigs"]
    palavras_problema = ["lento", "lenta", "erro", "problema", "falha",
                         "travando", "travado", "caiu", "fora", "parou",
                         "nao funciona", "não funciona",
                         "nao abre", "não abre",
                         "nao carrega", "não carrega",
                         "nao entra", "não entra",
                         "nao consigo", "não consigo"]

    tem_sistema = any(p in pergunta_lower for p in palavras_sistema)
    tem_problema = any(p in pergunta_lower for p in palavras_problema)

    if tem_sistema and tem_problema:
        for bloco in perguntas_faq:
            if "suporte" in bloco["titulo"].lower() or "atend" in bloco["titulo"].lower():
                bloco["_score"] = 999
                return bloco

    # --------------------------------------------------
    # REGRA 3: pergunta simples (curta) sobre suporte
    # --------------------------------------------------
    palavras_suporte_simples = ["suporte", "atendimento", "ajuda", "chamado", "ticket"]

    # Considera "simples" se tem até 3 palavras
    # OU se tem uma palavra de suporte + um verbo de ação
    palavras_acao_curta = ["preciso", "quero", "precisando", "tem", "como"]

    palavras_limpas = pergunta_lower.split()
    tem_palavra_suporte = any(p in palavras_limpas for p in palavras_suporte_simples)
    tem_acao_curta = any(p in palavras_limpas for p in palavras_acao_curta)

    if tem_palavra_suporte and (len(palavras_limpas) <= 3 or tem_acao_curta):
        for bloco in perguntas_faq:
            if "suporte" in bloco["titulo"].lower() or "atend" in bloco["titulo"].lower():
                bloco["_score"] = 999
                return bloco
            
    # --------------------------------------------------
    # REGRA 4: pergunta com "site" + algo de suporte → bloco de suporte
    # --------------------------------------------------
    palavras_site = ["site", "url", "link", "endereco", "endereço", "portal"]
    palavras_suporte_para_site = ["atendimento", "atende", "suporte", "dti", "chamado", "ticket"]

    tem_site = any(p in pergunta_lower for p in palavras_site)
    tem_suporte_em_site = any(p in pergunta_lower for p in palavras_suporte_para_site)

    if tem_site and tem_suporte_em_site:
        for bloco in perguntas_faq:
            if "suporte" in bloco["titulo"].lower() or "atend" in bloco["titulo"].lower():
                bloco["_score"] = 999
                return bloco

    # --------------------------------------------------
    # REGRA 5: palavras de RH → SIGRH (Portal do Servidor)
    # --------------------------------------------------
    palavras_rh = [
        "contracheque", "holerite", "salario", "salário", "remuneracao",
        "remuneração", "pagamento", "ferias", "férias", "ponto",
        "sigrh", "servidor", "funcional"
    ]
    if any(p in pergunta_lower for p in palavras_rh):
        for bloco in perguntas_faq:
            titulo_lower = bloco["titulo"].lower()
            if "sigrh" in titulo_lower and ("portal" in titulo_lower or "servidor" in titulo_lower):
                bloco["_score"] = 999
                return bloco

    # --------------------------------------------------
    # BUSCA NORMAL (RAG + Fuzz)
    # --------------------------------------------------
    if not rag_disponivel:
        return buscar_resposta(pergunta_usuario)

    emb_pergunta = _modelo_rag.encode([pergunta_usuario])
    similaridades = cos_sim(emb_pergunta, _embeddings_base)[0].numpy()
    indices_top = np.argsort(-similaridades)[:top_k_rag]

    candidatos = []
    for i in indices_top:
        score_rag = float(similaridades[i])
        if score_rag < 0.15:
            continue
        bloco = perguntas_faq[i]
        candidatos.append((bloco, score_rag))

    if not candidatos:
        return None

    pergunta_limpa = limpar_texto(pergunta_usuario)
    palavras_usuario = set(pergunta_limpa.split())
    palavras_usuario_expandidas = expandir_sinonimos(palavras_usuario)

    melhor = None
    melhor_score = 0

    for bloco, score_rag in candidatos:
        titulo = limpar_texto(bloco["titulo"])
        conteudo = limpar_texto(bloco["conteudo"])
        palavras_titulo = set(titulo.split())

        intersecao = palavras_usuario_expandidas & palavras_titulo

        score_titulo_set = fuzz.token_set_ratio(pergunta_limpa, titulo)
        score_titulo_sort = fuzz.token_sort_ratio(pergunta_limpa, titulo)
        score_titulo = max(score_titulo_set, score_titulo_sort)
        score_conteudo = fuzz.token_set_ratio(pergunta_limpa, conteudo)

        comuns_raras = intersecao & PALAVRAS_DISCRIMINATIVAS
        bonus = len(comuns_raras) * 5

        if palavras_usuario:
            cobertura = len(intersecao) / len(palavras_usuario)
            bonus_cobertura = cobertura * 20
        else:
            bonus_cobertura = 0

        bonus_rag_sem_palavras = 0
        if not intersecao:
            if score_rag >= 0.45:
                bonus_rag_sem_palavras = 25
            elif score_rag >= 0.35:
                bonus_rag_sem_palavras = 10
            else:
                bonus_rag_sem_palavras = -20

        n_palavras_titulo = len(palavras_titulo)
        if n_palavras_titulo <= 2:
            bonus_titulo_curto = 25
        elif n_palavras_titulo <= 4:
            bonus_titulo_curto = 15
        elif n_palavras_titulo <= 7:
            bonus_titulo_curto = 5
        else:
            bonus_titulo_curto = 0

        tamanho_conteudo = len(bloco["conteudo"])
        if tamanho_conteudo < 100:
            penalidade = 10
        elif tamanho_conteudo < 300:
            penalidade = 5
        else:
            penalidade = 0

        pontuacao = (
            (score_titulo * 0.6)
            + (score_conteudo * 0.1)
            + (score_rag * 100 * 0.3)
            + bonus
            + bonus_cobertura
            + bonus_rag_sem_palavras
            + bonus_titulo_curto
            - penalidade
        )

        if pontuacao > melhor_score:
            melhor_score = pontuacao
            melhor = bloco

    if melhor is None or melhor_score < 60:
        return None

    melhor["_score"] = round(melhor_score, 2)
    return melhor


# --------------------------------------------------
# REGISTRAR PERGUNTAS NÃO ENCONTRADAS
# --------------------------------------------------

ARQUIVO_NAO_ENCONTRADAS = "perguntas_nao_encontradas.txt"


def registrar_nao_encontrada(pergunta):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    linha = f"[{agora}] {pergunta}\n"

    with open(ARQUIVO_NAO_ENCONTRADAS, "a", encoding="utf-8") as arquivo:
        arquivo.write(linha)


# --------------------------------------------------
# REGISTRAR FEEDBACK (👍 / 👎)
# --------------------------------------------------

ARQUIVO_FEEDBACK = "feedback.txt"


def registrar_feedback(pergunta, titulo_faq, voto):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    linha = f"[{agora}] {voto} | Pergunta: {pergunta} | Resposta: {titulo_faq}\n"

    with open(ARQUIVO_FEEDBACK, "a", encoding="utf-8") as arquivo:
        arquivo.write(linha)

# --------------------------------------------------
# SUGESTÕES DE USUÁRIOS (/feedback)
# --------------------------------------------------

ARQUIVO_SUGESTOES = "sugestoes.txt"


def registrar_sugestao(user_id, sugestao):
    """Salva uma sugestão enviada pelo usuário."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    linha = f"[{agora}] {user_id}: {sugestao}\n"

    with open(ARQUIVO_SUGESTOES, "a", encoding="utf-8") as arquivo:
        arquivo.write(linha)


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /feedback: recebe sugestões dos usuários."""
    user_id = str(update.effective_user.id) if update.effective_user else "?"

    # Pega o texto depois do comando
    texto = " ".join(context.args) if context.args else ""

    if not texto:
        await update.message.reply_text(
            "<b>💬 Enviar sugestão</b>\n\n"
            "Escreva sua sugestão junto com o comando. Exemplos:\n"
            "• <code>/feedback Adicionar informação sobre VPN</code>\n"
            "• <code>/feedback Melhorar resposta sobre o SIGAA</code>\n"
            "• <code>/feedback Incluir tutorial de impressão</code>\n\n"
            "<i>Suas sugestões nos ajudam a melhorar o bot.</i>",
            parse_mode="HTML"
        )
        return

    # Limita o tamanho da sugestão
    texto = texto.strip()[:500]

    registrar_sugestao(user_id, texto)

    await update.message.reply_text(
        "✅ <b>Feedback registrado!</b>\n\n"
        "Obrigado pela sugestão. Ela será analisada pela equipe responsável.",
        parse_mode="HTML"
    )

# --------------------------------------------------
# HISTÓRICO DE CONVERSA (persistente em arquivo)
# --------------------------------------------------

ARQUIVO_HISTORICO = "historico.json"
MAX_HISTORICO = 2              # máx de interações guardadas por usuário
DIAS_INATIVIDADE = 30          # apaga histórico sem uso há N dias

_historico_global = {}         # cache em memória


def _carregar_historico_do_arquivo():
    """Lê o historico.json do disco para o cache."""
    global _historico_global

    # Arquivo não existe → começa vazio
    if not os.path.exists(ARQUIVO_HISTORICO):
        _historico_global = {}
        print("Histórico carregado: 0 usuários (arquivo novo)")
        return

    # Arquivo existe mas está vazio → começa vazio
    if os.path.getsize(ARQUIVO_HISTORICO) == 0:
        _historico_global = {}
        print("Histórico carregado: 0 usuários (arquivo vazio)")
        return

    try:
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            _historico_global = json.load(f)
        print(f"Histórico carregado: {len(_historico_global)} usuários")
    except Exception as e:
        print(f"ERRO ao carregar histórico: {e}")
        _historico_global = {}


def _salvar_historico_no_arquivo():
    """Grava o cache no disco de forma atômica."""
    try:
        tmp = ARQUIVO_HISTORICO + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_historico_global, f, ensure_ascii=False, indent=2)
        os.replace(tmp, ARQUIVO_HISTORICO)
        print(f"Histórico salvo: {len(_historico_global)} usuários", flush=True)
    except Exception as e:
        print(f"ERRO ao salvar histórico: {e}", flush=True)


def _limpar_historicos_antigos():
    """Remove históricos sem uso há mais de DIAS_INATIVIDADE dias."""
    from datetime import timedelta
    corte = (datetime.now() - timedelta(days=DIAS_INATIVIDADE)).timestamp()
    removidos = 0

    for user_id in list(_historico_global.keys()):
        info = _historico_global[user_id]
        if info.get("ultimo_uso", 0) < corte:
            del _historico_global[user_id]
            removidos += 1

    if removidos:
        print(f"Históricos removidos por inatividade: {removidos}")
        _salvar_historico_no_arquivo()


def obter_historico_por_id(user_id):
    """Retorna o histórico de um usuário pelo ID."""
    if not user_id:
        return []
    info = _historico_global.get(str(user_id), {})
    return info.get("interacoes", [])


def salvar_no_historico_por_id(user_id, pergunta, resposta):
    """Salva uma interação no histórico persistente do usuário."""

    # Remove formatação Markdown/HTML da resposta antes de salvar
    # (para o /historico mostrar texto limpo)
    # Remove TODAS as tags HTML/Markdown (evita erro no Telegram)
    import re as _re
    resposta = _re.sub(r"<[^>]+>", "", resposta)   # remove <tag>
    resposta = _re.sub(r"\*\*(.+?)\*\*", r"\1", resposta)  # **texto** → texto
    resposta = _re.sub(r"__(.+?)__", r"\1", resposta)      # __texto__ → texto
    resposta = resposta.replace("`", "")
    resposta = resposta.replace("*", "")
    resposta = resposta.replace("_", " ")
    if not user_id:
        print(" user_id vazio, não salva", flush=True)
        return
    user_id = str(user_id)



    if user_id not in _historico_global:
        _historico_global[user_id] = {
            "interacoes": [],
            "ultimo_uso": 0
        }

    info = _historico_global[user_id]
    info["interacoes"].append({
        "pergunta": pergunta,
        "resposta": resposta,
    })
    info["interacoes"] = info["interacoes"][-MAX_HISTORICO:]
    info["ultimo_uso"] = datetime.now().timestamp()

    _salvar_historico_no_arquivo()
    print(f" histórico salvo para {user_id}", flush=True)


def apagar_historico_por_id(user_id):
    """Apaga o histórico de um usuário pelo ID."""
    if not user_id:
        return
    user_id = str(user_id)
    if user_id in _historico_global:
        del _historico_global[user_id]
        _salvar_historico_no_arquivo()
        print(f" histórico apagado para {user_id}", flush=True)


# Carrega o histórico na inicialização
_carregar_historico_do_arquivo()
_limpar_historicos_antigos()


# --------------------------------------------------
# COMANDO /START
# --------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Limpeza extra: converter Markdown residual para HTML
    resposta = resposta.replace("**", "")  # Remove asteriscos duplos
    # Converte *texto* para <b>texto</b> (se houver)
    import re as _re
    resposta = _re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<b>\1</b>", resposta)
    await update.message.reply_text(
        "Olá! 👋\n\n"
        "Sou o Assistente da Wiki UFCA.\n"
        "Posso responder dúvidas sobre:\n\n"
        "• SIPAC (processos, despachos, documentos)\n"
        "• Rede Wi-Fi, Eduroam, VPN\n"
        "• SIGAA, SIGRH, SIGs, Office 365\n"
        "• Impressão, arquivos, assinatura digital\n\n"
        "Pode enviar sua dúvida!\n\n"
        "Digite /ajuda para ver exemplos de perguntas."
    )
    

# --------------------------------------------------
# COMANDO /AJUDA
# --------------------------------------------------

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>📚 Assistente da Wiki UFCA</b>\n\n"
        "Sou um bot que responde dúvidas sobre a UFCA "
        "com base em fontes oficiais (Wiki UFCA).\n\n"
        "<b>💬 Como perguntar:</b>\n"
        "Escreva sua dúvida em linguagem natural. Exemplos:\n\n"
        "<b>📋 SIPAC (processos):</b>\n"
        "• Como adicionar um despacho?\n"
        "• Como cancelar um documento?\n"
        "• Como consultar a unidade atual?\n\n"
        "<b>🌐 Rede e sistemas:</b>\n"
        "• Como conectar no Wi-Fi?\n"
        "• Configurar Eduroam\n"
        "• Esqueci a senha do SIGAA\n"
        "• Como instalar o Office?\n\n"
        "<b>🆘 Suporte:</b>\n"
        "• Como abrir um chamado?\n"
        "• Onde fica a DTI?\n\n"
        "<b>📌 Comandos disponíveis:</b>\n"
        "• /ajuda — esta mensagem\n"
        "• /exemplos — mais exemplos\n"
        "• /status — estatísticas do bot\n"
        "• /historico — suas perguntas\n"
        "• /limpar — apagar histórico\n"
        "• /feedback — enviar sugestão\n\n"
        "<b>⚠️ Importante:</b>\n"
        "Não invento respostas. Se não encontrar na base, "
        "indico o link oficial ou o Atende UFCA.",
        parse_mode="HTML"
    )
# --------------------------------------------------
# COMANDO /EXEMPLOS
# --------------------------------------------------
async def exemplos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>💬 Exemplos de perguntas que eu respondo</b>\n\n"
        "<b>📋 SIPAC (processos):</b>\n"
        "• Como adicionar um despacho?\n"
        "• Como cancelar um documento?\n"
        "• Como consultar a unidade atual?\n"
        "• Como acessar processo sigiloso?\n"
        "• Como tramitar um processo?\n\n"
        "<b>🌐 Rede:</b>\n"
        "• Como conectar no Wi-Fi?\n"
        "• Como configurar Eduroam no Linux?\n"
        "• Onde fica a DTI?\n\n"
        "<b>📧 Sistemas:</b>\n"
        "• Como acessar meu e-mail?\n"
        "• Esqueci a senha do SIGAA\n"
        "• Como instalar o Office?\n"
        "• Como acessar o Moodle?\n"
        "• Como consultar o contracheque?\n\n"
        "<b>🎥 Reuniões online:</b>\n"
        "• Como fazer reunião no Conferência Web?\n\n"
        "<b>🆘 Suporte:</b>\n"
        "• Como abrir um chamado?\n"
        "• Qual o site do atendimento?\n"
        "• Preciso de ajuda\n\n"
        "<i>É só escrever sua dúvida que eu busco na base oficial.</i>",
        parse_mode="HTML"
    )
# --------------------------------------------------
# COMANDO /STATUS (painel de controle)
# --------------------------------------------------

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_base = len(perguntas_faq)

    nao_encontradas = 0
    if os.path.exists(ARQUIVO_NAO_ENCONTRADAS):
        with open(ARQUIVO_NAO_ENCONTRADAS, "r", encoding="utf-8") as f:
            nao_encontradas = len([l for l in f if l.strip()])

    positivos = 0
    negativos = 0
    if os.path.exists(ARQUIVO_FEEDBACK):
        with open(ARQUIVO_FEEDBACK, "r", encoding="utf-8") as f:
            for linha in f:
                if "👍" in linha:
                    positivos += 1
                elif "👎" in linha:
                    negativos += 1

    total_feedbacks = positivos + negativos
    if total_feedbacks > 0:
        taxa = (positivos / total_feedbacks) * 100
        taxa_str = f"{taxa:.0f}%"
    else:
        taxa_str = "sem dados ainda"

    if os.path.exists(ARQUIVO_FAQ):
        mtime = os.path.getmtime(ARQUIVO_FAQ)
        ultima = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    else:
        ultima = "?"

    # Conta sugestões
    sugestoes = 0
    if os.path.exists(ARQUIVO_SUGESTOES):
        with open(ARQUIVO_SUGESTOES, "r", encoding="utf-8") as f:
            sugestoes = len([l for l in f if l.strip()])

    mensagem = (
        "📊 <b>Painel do Bot</b>\n\n"
        f"📚 Base: <b>{total_base}</b> blocos carregados\n"
        f"❓ Perguntas não encontradas: <b>{nao_encontradas}</b>\n"
        f"👍 Feedbacks positivos: <b>{positivos}</b>\n"
        f"👎 Feedbacks negativos: <b>{negativos}</b>\n"
        f"💬 Sugestões recebidas: <b>{sugestoes}</b>\n"
        f"📈 Taxa de acerto: <b>{taxa_str}</b>\n\n"
        f"🕐 Base atualizada em: {ultima}"
    )

    await update.message.reply_text(mensagem, parse_mode="HTML")


# --------------------------------------------------
# COMANDO /LIMPAR (apaga o histórico)
# --------------------------------------------------

async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id) if update.effective_user else None
    apagar_historico_por_id(user_id)

    await update.message.reply_text(
        "🧹 Histórico de conversa apagado.\n\n"
        "A partir de agora, vou responder sem lembrar das mensagens anteriores."
    )


# --------------------------------------------------
# COMANDO /HISTORICO (mostra o histórico)
# --------------------------------------------------
async def ver_historico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id) if update.effective_user else None
    historico = obter_historico_por_id(user_id)

    if not historico:
        await update.message.reply_text(
            "📭 Você ainda não tem histórico de conversa."
        )
        return

    import re as _re
    linhas = [f"📜 <b>Suas últimas {len(historico)} perguntas:</b>\n"]

    for i, h in enumerate(historico, start=1):
        # Limpa HTML/Markdown da resposta
        pergunta = h['pergunta']
        resposta = h['resposta'][:150].replace("\n", " ").strip()
        resposta = _re.sub(r"<[^>]+>", "", resposta)  # remove tags
        resposta = _re.sub(r"\*\*(.+?)\*\*", r"\1", resposta)
        resposta = resposta.replace("*", "").replace("_", " ")
        resposta = resposta.replace("`", "")
        resposta = resposta.replace("&", "&amp;")  # escapa
        resposta = resposta.replace("<", "&lt;").replace(">", "&gt;")  # escapa

        # Escapa a pergunta também
        pergunta = pergunta.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        linhas.append(f"<b>{i}. {pergunta}</b>")
        linhas.append(f"   <i>→ {resposta}...</i>")
        linhas.append("")

    linhas.append(f"<i>Use /limpar para apagar o histórico.</i>")

    try:
        await update.message.reply_text(
            "\n".join(linhas),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"ERRO ao enviar /historico: {e}", flush=True)
        await update.message.reply_text(
            "📜 Histórico disponível, mas houve um erro ao formatar. "
            "Use /limpar para começar de novo."
        )

# --------------------------------------------------
# RESPONDER PERGUNTAS
# --------------------------------------------------

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    pergunta = update.message.text
    print(f" responder chamado: {pergunta!r}", flush=True)
    user_id = str(update.effective_user.id) if update.effective_user else None
    print(f" user_id do update: {user_id}", flush=True)

    if eh_saudacao(pergunta):
        await update.message.reply_text(
            "Oi! 👋 Pode mandar sua dúvida sobre o SIPAC que eu ajudo a encontrar a informação certa."
        )
        return

    # Combina com a pergunta anterior se for continuação
    pergunta_para_busca = combinar_com_historico(pergunta, user_id)
    resultado = buscar_resposta_hibrida(pergunta_para_busca)

    if resultado:
        conteudo = resultado["conteudo"].strip()

        conteudo_ruim = (
            len(conteudo) < 50
            or ".responsive-embed" in conteudo
            or conteudo.count("{") > 3
            or "position:" in conteudo
        )

        if conteudo_ruim:
            resposta = (
                "🔍 Encontrei a página oficial sobre esse assunto, mas o "
                "conteúdo dela não está disponível para consulta automática "
                "(a página exige permissão especial de acesso).\n\n"
                "📄 Pergunta do FAQ:\n"
                f"{resultado['titulo']}\n\n"
                "🔗 Acesse diretamente no site oficial:\n"
                f"{resultado['link']}"
            )
            texto_para_historico = resposta

        else:
            await update.message.chat.send_action(action=ChatAction.TYPING)

            texto_ia = gerar_resposta_ia(
                pergunta_usuario=pergunta,
                titulo_faq=resultado["titulo"],
                conteudo_faq=conteudo,
                historico=obter_historico_por_id(user_id)
            )

            resposta = (
                f"{texto_ia}\n\n"
                f"🔗 Fonte oficial:\n"
                f"{resultado['link']}"
            )
            texto_para_historico = texto_ia

        botoes = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👍 Ajudou", callback_data="feedback_ok"),
                InlineKeyboardButton("👎 Não ajudou", callback_data="feedback_ruim"),
            ]
        ])

        context.user_data["ultima_pergunta"] = pergunta
        context.user_data["ultimo_titulo"] = resultado["titulo"]

        # 📜 Salva no histórico
        salvar_no_historico_por_id(user_id, pergunta, texto_para_historico)
        

        await update.message.reply_text(
    resposta,
    reply_markup=botoes,
    parse_mode="HTML"
)

    else:
        registrar_nao_encontrada(pergunta)

        resposta = (
            "❌ Não encontrei uma informação relacionada "
            "à sua dúvida na base oficial da UFCA.\n\n"
            "💡 <b>Tente reformular usando outras palavras:</b>\n"
            "• 'documento' → 'despacho' / 'arquivo'\n"
            "• 'caiu' → 'erro' / 'não funciona'\n"
            "• 'lento' → 'travando' / 'problema'\n\n"
            "📚 <b>Assuntos que eu domino:</b>\n"
            "• SIPAC — processos, despachos, documentos, tramitação\n"
            "• Rede — Wi-Fi, Eduroam, VPN\n"
            "• Sistemas — SIGAA, SIGRH, Office 365, e-mail\n"
            "• Serviços — impressão, arquivos, assinatura digital\n"
            "• Suporte — Atende UFCA, DTI\n\n"
            "💬 <b>Exemplos de perguntas:</b>\n"
            "• Como adicionar um despacho?\n"
            "• Como consultar a unidade atual?\n"
            "• Como tramitar um processo?\n"
            "• Como conectar no Wi-Fi?\n\n"
            "🆘 <b>Se não encontrou, abra um chamado:</b>\n"
            "https://atendimento.ufca.edu.br\n\n"
            "Digite /ajuda para mais exemplos."
        )

        await update.message.reply_text(resposta, parse_mode="HTML")

# --------------------------------------------------
# DETECTAR PERGUNTAS QUE PRECISAM DE CONTEXTO
# --------------------------------------------------

PALAVRAS_CONTINUACAO = {
    "e", "também", "tambem", "isso", "esse", "essa", "este", "esta",
    "aquilo", "aquela", "aquele", "mais", "outro", "outra",
}

# Frases que começam com essas palavras são continuações
PREFIXOS_CONTINUACAO = ["e ", "também ", "tambem ", "e o ", "e a ", "e os ", "e as "]


def precisa_contexto(pergunta):
    """
    Retorna True se a pergunta é uma continuação que precisa
    do contexto anterior (ex: "e no Linux?", "também funciona?").
    """
    pergunta_lower = pergunta.lower().strip()
    palavras = pergunta_lower.split()

    # 1. Se a pergunta tem 1 palavra, é continuação
    if len(palavras) <= 1:
        return True

    # 2. Se começa com um PREFIXO de continuação, é continuação
    # (mas o prefixo precisa ser seguido de POUCAS palavras)
    for prefixo in PREFIXOS_CONTINUACAO:
        if pergunta_lower.startswith(prefixo):
            return True

    # 3. Se tem poucas palavras (2-3) E tem palavra de continuação
    # (e, também, isso, mais, aí, etc), é continuação
    if len(palavras) <= 3:
        for p in palavras:
            if p in PALAVRAS_CONTINUACAO:
                return True

    # 4. Caso contrário, NÃO é continuação
    return False


def combinar_com_historico(pergunta, user_id):
    """
    Se a pergunta precisa de contexto, junta com a anterior.
    Caso contrário, retorna a própria pergunta.
    """
    if not precisa_contexto(pergunta):
        return pergunta

    historico = obter_historico_por_id(user_id)
    if not historico:
        return pergunta

    ultima = historico[-1]["pergunta"]
    combinada = f"{ultima} {pergunta}"
    print(f"[contexto] combinando: {combinada!r}", flush=True)
    return combinada

# --------------------------------------------------
# TRATAR CLIQUE NO BOTÃO DE FEEDBACK
# --------------------------------------------------

async def tratar_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pergunta = context.user_data.get("ultima_pergunta", "?")
    titulo = context.user_data.get("ultimo_titulo", "?")

    if query.data == "feedback_ok":
        voto = "👍"
        mensagem = "Obrigado pelo feedback! 😊"
    else:
        voto = "👎"
        mensagem = (
            "Obrigado! Vou registrar isso para melhorar. 🙏\n"
            "Se puder, tente reformular a pergunta."
        )

    registrar_feedback(pergunta, titulo, voto)

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(mensagem)


# --------------------------------------------------
# INICIAR BOT
# --------------------------------------------------

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ajuda", ajuda))
app.add_handler(CommandHandler("exemplos", exemplos))
app.add_handler(CommandHandler("feedback", feedback))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("limpar", limpar))
app.add_handler(CommandHandler("historico", ver_historico))
app.add_handler(CallbackQueryHandler(tratar_feedback))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, responder)
)

if __name__ == "__main__":
    print("Bot iniciado!", flush=True)
    try:
        app.run_polling(
            drop_pending_updates=True,
            close_loop=True,
        )
    except KeyboardInterrupt:
        print("Bot interrompido pelo usuário.", flush=True)
    except Exception as e:
        print(f"ERRO FATAL: {type(e).__name__}: {e}", flush=True)
        raise
