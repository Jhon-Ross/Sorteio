import csv
from database import create_tables, engine, Token, Base, SessionLocal
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def reset_database():
    logging.info("🗑️ Removendo tabelas existentes...")
    Base.metadata.drop_all(bind=engine)
    
    logging.info("📦 Criando novas tabelas...")
    create_tables()

def load_tokens_from_csv():
    logging.info("📝 Carregando tokens do arquivo CSV...")
    db = SessionLocal()
    try:
        # Lê o arquivo CSV e insere os tokens
        with open('tokens.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Pula o cabeçalho
            tokens = []
            for row in reader:
                if row:  # Verifica se a linha não está vazia
                    token = Token(number=row[0], is_used=False)
                    tokens.append(token)
            
            # Insere todos os tokens de uma vez
            db.bulk_save_objects(tokens)
            db.commit()
            logging.info(f"✅ {len(tokens)} tokens inseridos com sucesso!")
    except Exception as e:
        logging.error(f"❌ Erro ao carregar tokens: {e}")
        db.rollback()
    finally:
        db.close()

def verify_database():
    db = SessionLocal()
    try:
        # Verifica quantidade de tokens
        token_count = db.query(Token).count()
        unused_token_count = db.query(Token).filter_by(is_used=False).count()
        used_token_count = db.query(Token).filter_by(is_used=True).count()
        
        logging.info("\n=== Status do Banco de Dados ===")
        logging.info(f"📊 Total de tokens: {token_count}")
        logging.info(f"🟢 Tokens disponíveis: {unused_token_count}")
        logging.info(f"🔴 Tokens usados: {used_token_count}")
        logging.info("============================\n")
        
    except Exception as e:
        logging.error(f"❌ Erro ao verificar banco de dados: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    logging.info("🚀 Iniciando reset do banco de dados...")
    reset_database()
    load_tokens_from_csv()
    verify_database()
    logging.info("✨ Processo finalizado!") 