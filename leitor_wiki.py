import requests
from bs4 import BeautifulSoup
import time

HEADERS = {"User-Agent": "Mozilla/5.0"}
ARQUIVO_SAIDA = "outras_paginas.txt"
URL_API = "https://wiki.ufca.edu.br/graphql"


def listar_paginas():
    """Pega a lista de todas as páginas da Wiki via GraphQL."""
    query = "{ pages { list { id path title } } }"
    r = requests.post(URL_API, json={"query": query}, headers={
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    })
    return r.json()["data"]["pages"]["list"]


def limpar_linha(linha):
    """
    Retorna True se a linha parece conteúdo real,
    False se parece CSS/código.
    """
    linha = linha.strip()
    if not linha:
        return False

    # Linhas que parecem CSS puro
    if linha.endswith("{"):
        return False
    if linha in ("}", "};"):
        return False
    if "px;" in linha or "em;" in linha or "%;" in linha:
        return False
    if "position:" in linha or "padding-" in linha or "margin:" in linha:
        return False
    if "height:" in linha or "width:" in linha or "border-" in linha:
        return False
    if "overflow:" in linha or "display:" in linha:
        return False

    return True


def pegar_conteudo(path):
    """Baixa o HTML da página e extrai só o texto."""
    url = f"https://wiki.ufca.edu.br/pt-br/{path}"
    r = requests.get(url, headers=HEADERS, timeout=15)

    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html5lib")

    # Tenta achar o container do conteúdo principal
    conteudo = soup.find("main")
    if not conteudo:
        conteudo = soup.find("div", class_="contents")
    if not conteudo:
        conteudo = soup.find("div", id="root")
    if not conteudo:
        conteudo = soup.body

    if not conteudo:
        return None

    # Remove tags que não são conteúdo
    for el in conteudo.find_all([
        "script", "style", "nav", "header", "footer",
        "iframe", "noscript", "svg", "form", "button"
    ]):
        el.decompose()

    texto = conteudo.get_text("\n", strip=True)

    # Filtra linha por linha, removendo CSS
    linhas_boas = [l for l in texto.split("\n") if limpar_linha(l)]
    texto_limpo = "\n".join(linhas_boas)

    # Remove âncora
    texto_limpo = texto_limpo.replace("¶", "").strip()

    return texto_limpo


def main():
    paginas = listar_paginas()
    print(f"Total de páginas na Wiki: {len(paginas)}\n")

    # Filtra: pula a home e a FAQ do SIPAC (que já temos)
    para_processar = []
    for p in paginas:
        path = p["path"]
        if path == "home":
            continue
        if "faqSipac" in path:
            continue
        para_processar.append(p)

    print(f"Páginas para processar: {len(para_processar)}\n")

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as arquivo:
        for i, p in enumerate(para_processar, start=1):
            titulo = p["title"]
            path = p["path"]

            print(f"[{i}/{len(para_processar)}] {titulo[:60]}")

            conteudo = pegar_conteudo(path)

            if conteudo is None or len(conteudo) < 20:
                print(f"   -> BLOQUEADO ou vazio, pulando")
                continue

            arquivo.write("=" * 70 + "\n")
            arquivo.write(f"{titulo}\n")
            arquivo.write(f"https://wiki.ufca.edu.br/pt-br/{path}\n\n")
            arquivo.write(conteudo + "\n")
            arquivo.write("=" * 70 + "\n\n")

            print(f"   -> OK ({len(conteudo)} chars)")
            time.sleep(0.5)

    print(f"\nPronto! Salvo em {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()
