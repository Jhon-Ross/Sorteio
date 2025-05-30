import random
import string
import csv


def gerar_tokens(quantidade):
    tokens = set()

    while len(tokens) < quantidade:
        letra = random.choice(string.ascii_uppercase)  # Letra de A a Z
        numeros = f"{random.randint(0, 999):03d}"       # Número com 3 dígitos
        token = f"{letra}{numeros}"
        tokens.add(token)

    return list(tokens)


# Gerar 2500 tokens
tokens = gerar_tokens(2500)

# Salvar em um arquivo CSV
with open("tokens.csv", "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Token"])  # Cabeçalho da coluna
    for token in tokens:
        writer.writerow([token])

print("Tokens salvos com sucesso em 'tokens.csv'.")
