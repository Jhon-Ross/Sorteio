from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv
from datetime import datetime
import logging
import urllib.parse
import time

# Carrega variáveis de ambiente
load_dotenv()

# Configuração do banco de dados
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não está configurada nas variáveis de ambiente!")

# Adiciona parâmetros SSL e conexão à URL do banco de dados
if 'pooler.supabase.com' in DATABASE_URL:
    parsed_url = urllib.parse.urlparse(DATABASE_URL)
    query_params = dict(urllib.parse.parse_qsl(parsed_url.query))
    
    # Adiciona parâmetros SSL e outros parâmetros importantes
    query_params.update({
        'sslmode': 'require',
        'connect_timeout': '10',  # Reduzido para transaction pooler
        'application_name': 'sorteio_app'
    })
    
    # Reconstrói a URL com os novos parâmetros
    new_query = urllib.parse.urlencode(query_params)
    DATABASE_URL = urllib.parse.urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        parsed_url.fragment
    ))

logging.info(f"Conectando ao banco de dados usando Transaction Pooler...")

# Configurações do pool otimizadas para transaction pooler
pool_size = 20  # Aumentado para transaction pooler
max_overflow = 10
pool_timeout = 30

# Cria o engine do SQLAlchemy com configurações de pool
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_timeout=pool_timeout,
    pool_pre_ping=True,
    pool_recycle=1800,  # Recicla conexões a cada 30 minutos
    connect_args={
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000'  # 30 segundos timeout para statements
    }
)

# Cria a sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria a base declarativa
Base = declarative_base()

class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, index=True, nullable=False)
    is_used = Column(Boolean, default=False)
    
    # Dados do comprador (imutáveis após a compra)
    owner_name = Column(String)
    owner_email = Column(String)
    owner_cpf = Column(String)
    owner_phone = Column(String)
    
    # Dados do pagamento (imutáveis após a compra)
    payment_id = Column(String)
    payment_status = Column(String)
    external_reference = Column(String, index=True)  # Adicionado index para melhorar performance
    purchase_date = Column(DateTime, default=datetime.utcnow)
    total_amount = Column(Float)

def get_db(max_retries=3, retry_delay=1):
    """
    Obtém uma conexão com o banco de dados com mecanismo de retry
    
    Args:
        max_retries (int): Número máximo de tentativas de conexão
        retry_delay (int): Tempo de espera entre tentativas em segundos
    """
    db = None
    attempt = 0
    last_error = None
    
    while attempt < max_retries:
        try:
            db = SessionLocal()
            # Testa a conexão com timeout
            db.execute("SELECT 1")
            return db
        except Exception as e:
            last_error = e
            if db:
                db.close()
            
            attempt += 1
            if attempt < max_retries:
                logging.warning(f"Tentativa {attempt} de {max_retries} falhou. Tentando novamente em {retry_delay} segundos...")
                time.sleep(retry_delay)
            db = None
    
    logging.error(f"Todas as {max_retries} tentativas de conexão falharam. Último erro: {str(last_error)}")
    raise last_error

# Função para criar todas as tabelas
def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        logging.info("Tabelas criadas com sucesso!")
    except Exception as e:
        logging.error(f"Erro ao criar tabelas: {str(e)}")
        raise 