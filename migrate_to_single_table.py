from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, MetaData, Table, text
from database import SessionLocal, Base, engine
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_new_tokens_table():
    metadata = MetaData()
    
    # Criando a nova tabela de tokens
    new_tokens = Table(
        'new_tokens', metadata,
        Column('id', Integer, primary_key=True),
        Column('number', String, unique=True, nullable=False),
        Column('is_used', Boolean, default=False),
        Column('owner_name', String),
        Column('owner_email', String),
        Column('owner_cpf', String),
        Column('owner_phone', String),
        Column('payment_id', String),
        Column('payment_status', String),
        Column('external_reference', String),
        Column('purchase_date', DateTime),
        Column('total_amount', Float),
    )
    
    logger.info("Criando nova tabela de tokens...")
    metadata.create_all(engine)
    return new_tokens

def migrate_data():
    with engine.begin() as conn:
        try:
            # Criar nova tabela
            new_tokens = create_new_tokens_table()
            
            # Migrar dados
            logger.info("Iniciando migração dos dados...")
            
            # Primeiro, inserir todos os tokens não utilizados usando SQL direto
            sql_unused = text("""
                SELECT number, is_used
                FROM tokens
                WHERE is_used = false
            """)
            
            unused_tokens = conn.execute(sql_unused).fetchall()
            unused_count = 0
            for token in unused_tokens:
                conn.execute(
                    new_tokens.insert(),
                    {
                        "number": token.number,
                        "is_used": False
                    }
                )
                unused_count += 1
            logger.info(f"Migrados {unused_count} tokens não utilizados")
            
            # Depois, inserir tokens utilizados com dados da compra
            sql_used = text("""
                SELECT t.number, t.is_used, 
                       p.name, p.email, p.cpf, p.phone,
                       p.payment_id, p.status as payment_status,
                       p.external_reference, p.created_at as purchase_date,
                       p.total_amount / p.quantity as token_amount
                FROM tokens t
                JOIN purchases p ON t.purchase_id = p.id
                WHERE t.is_used = true
            """)
            
            used_tokens = conn.execute(sql_used).fetchall()
            used_count = 0
            for token in used_tokens:
                conn.execute(
                    new_tokens.insert(),
                    {
                        "number": token.number,
                        "is_used": True,
                        "owner_name": token.name,
                        "owner_email": token.email,
                        "owner_cpf": token.cpf,
                        "owner_phone": token.phone,
                        "payment_id": token.payment_id,
                        "payment_status": token.payment_status,
                        "external_reference": token.external_reference,
                        "purchase_date": token.purchase_date,
                        "total_amount": token.token_amount
                    }
                )
                used_count += 1
            logger.info(f"Migrados {used_count} tokens utilizados")
            
            # Verificar migração usando SQL direto
            total_old = conn.execute(text("SELECT COUNT(*) FROM tokens")).scalar()
            total_new = conn.execute(text("SELECT COUNT(*) FROM new_tokens")).scalar()
            logger.info(f"Total de tokens na tabela antiga: {total_old}")
            logger.info(f"Total de tokens na tabela nova: {total_new}")
            
            if total_old == total_new:
                logger.info("✅ Migração concluída com sucesso!")
                
                # Backup das tabelas antigas
                conn.execute(text("ALTER TABLE tokens RENAME TO tokens_backup"))
                conn.execute(text("ALTER TABLE purchases RENAME TO purchases_backup"))
                
                # Renomear nova tabela
                conn.execute(text("ALTER TABLE new_tokens RENAME TO tokens"))
                
                logger.info("✅ Tabelas antigas renomeadas para backup e nova tabela ativada")
            else:
                raise Exception("❌ Erro na migração: total de tokens não confere!")
                
        except Exception as e:
            logger.error(f"❌ Erro durante a migração: {str(e)}")
            raise

def verify_migration():
    with engine.connect() as conn:
        try:
            logger.info("\n=== Verificando Migração ===")
            
            # Verificar alguns tokens aleatórios usando SQL direto
            sql = text("""
                SELECT number, owner_name, owner_email, payment_status, purchase_date
                FROM tokens
                WHERE is_used = true
                LIMIT 5
            """)
            tokens = conn.execute(sql).fetchall()
            
            for token in tokens:
                logger.info(f"\nToken: {token.number}")
                logger.info(f"Comprador: {token.owner_name}")
                logger.info(f"Email: {token.owner_email}")
                logger.info(f"Status: {token.payment_status}")
                logger.info(f"Data da Compra: {token.purchase_date}")
                
            # Contar totais usando SQL direto
            total_tokens = conn.execute(text("SELECT COUNT(*) FROM tokens")).scalar()
            used_tokens = conn.execute(text("SELECT COUNT(*) FROM tokens WHERE is_used = true")).scalar()
            logger.info(f"\nTotal de tokens: {total_tokens}")
            logger.info(f"Tokens vendidos: {used_tokens}")
            logger.info(f"Tokens disponíveis: {total_tokens - used_tokens}")
            
        except Exception as e:
            logger.error(f"❌ Erro durante a verificação: {str(e)}")
            raise

if __name__ == "__main__":
    logger.info("🚀 Iniciando processo de migração...")
    migrate_data()
    verify_migration()
    logger.info("✨ Processo de migração finalizado!") 