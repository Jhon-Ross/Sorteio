import os
import csv
import psycopg2
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

DATABASE_URL = os.getenv('POSTGRES_URL')

def populate_tokens_from_csv(caminho_csv='tokens.csv'):
    """Lê tokens de um arquivo CSV e os insere na tabela Tokens do banco de dados."""
    conn = None
    cur = None
    try:
        if not DATABASE_URL:
            print("Erro: A variável de ambiente POSTGRES_URL não está definida.")
            return

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        tokens_para_inserir = []
        try:
            with open(caminho_csv, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                header = next(reader) # Pula o cabeçalho, ex: "Token"
                if not header or header[0].strip().lower() != 'token':
                    print(f"Aviso: O cabeçalho esperado 'Token' não foi encontrado no CSV. O cabeçalho encontrado foi: {header}")
                    # Decide se quer continuar ou parar. Por agora, vamos continuar assumindo que a primeira coluna é o token.
                
                for row_number, row in enumerate(reader, start=2): # start=2 por causa do cabeçalho
                    if row and row[0].strip(): # Garante que a linha e o token não estão vazios
                        tokens_para_inserir.append((row[0].strip(),)) # Adiciona como tupla para executemany
                    else:
                        print(f"Aviso: Linha {row_number} do CSV está vazia ou token inválido e será ignorada.")
        
        except FileNotFoundError:
            print(f"Erro Crítico: Arquivo CSV '{caminho_csv}' não encontrado.")
            return
        except Exception as e_csv:
            print(f"Erro ao ler o arquivo CSV '{caminho_csv}': {e_csv}")
            return

        if not tokens_para_inserir:
            print("Nenhum token válido encontrado no CSV para inserir.")
            return

        # Usar executemany para inserção em lote é mais eficiente
        # ON CONFLICT (numero_token) DO NOTHING evita erros se você tentar inserir tokens duplicados
        # e garante que tokens já existentes não sejam alterados (mantendo seu estado 'disponivel')
        insert_query = "INSERT INTO Tokens (numero_token, disponivel) VALUES (%s, TRUE) ON CONFLICT (numero_token) DO NOTHING"
        
        cur.executemany(insert_query, tokens_para_inserir)
        conn.commit()
        
        print(f"{cur.rowcount} novos tokens foram inseridos na tabela 'Tokens' a partir de '{caminho_csv}'.")
        if cur.rowcount < len(tokens_para_inserir):
            print(f"{len(tokens_para_inserir) - cur.rowcount} tokens do CSV já existiam no banco de dados e não foram alterados.")

    except psycopg2.Error as e_db:
        print(f"Erro do Psycopg2 ao popular tokens: {e_db}")
        if conn:
            conn.rollback()
    except Exception as e_general:
        print(f"Um erro geral ocorreu ao popular tokens: {e_general}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == '__main__':
    print(f"Iniciando script para popular a tabela Tokens a partir do arquivo 'tokens.csv'...")
    # Certifique-se que o arquivo 'tokens.csv' está na mesma pasta que este script,
    # ou ajuste o caminho em populate_tokens_from_csv('caminho/correto/para/tokens.csv')
    populate_tokens_from_csv('tokens.csv') #
    print("Script para popular tokens finalizado.")