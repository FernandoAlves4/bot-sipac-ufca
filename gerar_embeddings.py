"""
Gera embeddings de todos os blocos da base de conhecimento
e salva num arquivo .pkl para uso rápido pelo bot.
"""
import os
import pickle
from sentence_transformers import SentenceTransformer

# Importa a função de carregamento do bot (para não duplicar código)
from bot import perguntas_faq

ARQUIVO_EMBEDDINGS = "embeddings.pkl"
MODELO = "paraphrase-multilingual-MiniLM-L12-v2"


def gerar():
    print(f"Total de blocos na base: {len(perguntas_faq)}")
    print(f"Carregando modelo '{MODELO}'...")
    model = SentenceTransformer(MODELO)

    print("Gerando embeddings...")
    textos = []
    for i, bloco in enumerate(perguntas_faq, start=1):
        
        # Usa só o título — é o sinal mais limpo e específico
        texto = bloco['titulo']
        textos.append(texto)
        if i % 10 == 0:
            print(f"  {i}/{len(perguntas_faq)} processados...")

    # Gera todos os embeddings de uma vez (mais rápido)
    embeddings = model.encode(textos, show_progress_bar=True)

    # Salva o modelo usado + os embeddings + os blocos
    dados = {
        "modelo": MODELO,
        "embeddings": embeddings,
        "blocos": perguntas_faq,
    }

    with open(ARQUIVO_EMBEDDINGS, "wb") as f:
        pickle.dump(dados, f)

    print(f"\n✅ Pronto! Salvo em {ARQUIVO_EMBEDDINGS}")
    print(f"   {len(embeddings)} embeddings de dimensão {embeddings.shape[1]}")


if __name__ == "__main__":
    gerar()
