import os
import psycopg2
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
# Garanta que seu .env tenha a variável POSTGRES_URL configurada
load_dotenv()

DATABASE_URL = os.getenv('POSTGRES_URL')

def create_tables():
    """Cria as tabelas Tokens e Adquiridos no banco de dados se não existirem."""
    conn = None
    cur = None  # Definir cur aqui para garantir que está acessível no finally
    try:
        if not DATABASE_URL:
            print("Erro: A variável de ambiente POSTGRES_URL não está definida.")
            print("Certifique-se de que ela está no seu arquivo .env e que o .env está na raiz do projeto.")
            return

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Criação da tabela Tokens
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Tokens (
                id SERIAL PRIMARY KEY,
                numero_token VARCHAR(10) UNIQUE NOT NULL,
                disponivel BOOLEAN DEFAULT TRUE,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Tabela 'Tokens' verificada/criada com sucesso.")

        # Criação da tabela Adquiridos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Adquiridos (
                id SERIAL PRIMARY KEY,
                token_id INTEGER REFERENCES Tokens(id),
                numero_token_adquirido VARCHAR(10),
                nome_cliente VARCHAR(255) NOT NULL,
                email_cliente VARCHAR(255) NOT NULL,
                cpf_cliente VARCHAR(20),
                telefone_cliente VARCHAR(50),
                payment_id_mp VARCHAR(255),      -- ID do pagamento no Mercado Pago
                order_id_interno VARCHAR(255) UNIQUE, -- Seu 'order_id' / external_reference do MP
                status_compra VARCHAR(50),       -- ex: 'pending', 'approved', 'rejected'
                total_pago DECIMAL(10, 2),       -- Valor total pago
                data_compra TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Tabela 'Adquiridos' verificada/criada com sucesso.")

        # Criação de Índices para otimizar buscas comuns (opcional, mas recomendado)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tokens_numero_token ON Tokens(numero_token);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tokens_disponivel ON Tokens(disponivel);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_adquiridos_token_id ON Adquiridos(token_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_adquiridos_email_cliente ON Adquiridos(email_cliente);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_adquiridos_order_id_interno ON Adquiridos(order_id_interno);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_adquiridos_status_compra ON Adquiridos(status_compra);")
        print("Índices verificados/criados com sucesso.")

        conn.commit()
        print("Transação comitada com sucesso.")

    except psycopg2.Error as e:
        print(f"Erro do Psycopg2 ao criar tabelas: {e}")
        if conn:
            conn.rollback()
            print("Rollback da transação realizado.")
    except Exception as e:
        print(f"Um erro geral ocorreu: {e}")
        if conn:
            conn.rollback()
            print("Rollback da transação realizado devido a erro geral.")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
            print("Conexão com o banco de dados fechada.")

if __name__ == '__main__':
    print("Iniciando script para criar tabelas...")
    create_tables()
    print("Script para criar tabelas finalizado.")