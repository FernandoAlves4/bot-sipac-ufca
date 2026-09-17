import requests
from bs4 import BeautifulSoup
import time
import re          
import requests    

HEADERS = {"User-Agent": "Mozilla/5.0"}


def pegar_perguntas():
    """Acessa a página da FAQ e retorna a lista de (pergunta, link)."""
    url = "https://wiki.ufca.edu.br/pt-br/dti/CSI/faqSipac"
    resposta = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resposta.text, "html5lib")

    perguntas = []

    for h3 in soup.find_all("h3", class_="toc-header"):
        link = h3.find("a", class_="is-internal-link")

        if link:
            texto = link.get_text(strip=True)
            endereco = link.get("href")

            if endereco.startswith("/"):
                endereco = "https://wiki.ufca.edu.br" + endereco

            perguntas.append((texto, endereco))

    return perguntas


def pegar_conteudo(url):
    """Acessa uma página individual e retorna só o texto da resposta."""
    resposta = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resposta.text, "html5lib")

    # Primeiro tenta encontrar o conteúdo principal
    conteudo = soup.find("div", id="root")

    # Se não encontrar, tenta outras estruturas comuns
    if not conteudo:
        conteudo = soup.find("main")

    if not conteudo:
        conteudo = soup.body

    if not conteudo:
        return "[Não foi possível extrair o conteúdo desta página]"

    # Remove partes que não são conteúdo da FAQ
    for elemento in conteudo.find_all(["script", "style", "nav", "header", "footer"]):
        elemento.decompose()

    texto = conteudo.get_text("\n", strip=True)

    # Corta a sobra de CSS
    if ".responsive-embed" in texto:
        texto = texto.split(".responsive-embed")[0]

    # Remove o símbolo de âncora
    texto = texto.replace("¶", "").strip()

    return texto


def main():
    perguntas = pegar_perguntas()
    print(f"Perguntas encontradas: {len(perguntas)}\n")

    with open("faq_sipac.txt", "w", encoding="utf-8") as arquivo:
        for i, (pergunta, link) in enumerate(perguntas, start=1):
            print(f"Processando {i}/{len(perguntas)}: {pergunta}")

            # 🔧 Remove o número que já vem duplicado da página
            # Ex: "10- Como associar..." → "Como associar..."
            pergunta_limpa = re.sub(r"^\d+\s*-?\s*", "", pergunta).strip()

            conteudo = pegar_conteudo(link)

            arquivo.write("=" * 70 + "\n")
            arquivo.write(f"{i:02d} - {pergunta_limpa}\n")
            arquivo.write(f"{link}\n\n")
            arquivo.write(conteudo + "\n")
            arquivo.write("=" * 70 + "\n\n")

            # Pausa curta entre requisições, para não sobrecarregar o servidor
            time.sleep(0.5)

    print("\nTudo pronto! Informações salvas em faq_sipac.txt")
    
if __name__ == "__main__":
    main()