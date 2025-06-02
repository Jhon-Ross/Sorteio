from database import SessionLocal, Token
from sqlalchemy import text

def verify_data_integrity():
    db = SessionLocal()
    try:
        print("🔍 Iniciando verificação de integridade dos dados...")
        
        # Verifica total de tokens
        total_tokens = db.query(Token).count()
        print(f"Total de tokens: {total_tokens}")
        if total_tokens != 2500:
            print(f"❌ Erro: Total de tokens ({total_tokens}) não é 2500!")
            return False
            
        # Verifica tokens vendidos
        used_tokens = db.query(Token).filter_by(is_used=True).all()
        print(f"Tokens vendidos: {len(used_tokens)}")
        
        # Verifica consistência dos dados dos tokens vendidos
        for token in used_tokens:
            if not all([
                token.owner_name,
                token.owner_email,
                token.owner_cpf,
                token.owner_phone,
                token.external_reference,
                token.payment_status,
                token.purchase_date,
                token.total_amount
            ]):
                print(f"❌ Erro: Token {token.number} tem dados incompletos!")
                return False
                
        # Verifica tokens disponíveis
        available_tokens = db.query(Token).filter_by(is_used=False).all()
        print(f"Tokens disponíveis: {len(available_tokens)}")
        
        # Verifica se os tokens disponíveis não têm dados de compra
        for token in available_tokens:
            if any([
                token.owner_name,
                token.owner_email,
                token.owner_cpf,
                token.owner_phone,
                token.external_reference,
                token.payment_status,
                token.purchase_date,
                token.total_amount
            ]):
                print(f"❌ Erro: Token não usado {token.number} tem dados de compra!")
                return False
                
        # Verifica se não há duplicatas de números
        sql = text("""
            SELECT number, COUNT(*) as count
            FROM tokens
            GROUP BY number
            HAVING COUNT(*) > 1
        """)
        duplicates = db.execute(sql).fetchall()
        if duplicates:
            print("❌ Erro: Encontrados números duplicados!")
            for dup in duplicates:
                print(f"Número {dup.number} aparece {dup.count} vezes")
            return False
            
        # Verifica se todos os tokens de uma compra têm os mesmos dados
        sql = text("""
            SELECT external_reference, 
                   COUNT(DISTINCT owner_name) as names,
                   COUNT(DISTINCT owner_email) as emails,
                   COUNT(DISTINCT owner_cpf) as cpfs,
                   COUNT(DISTINCT owner_phone) as phones,
                   COUNT(DISTINCT payment_status) as statuses
            FROM tokens
            WHERE external_reference IS NOT NULL
            GROUP BY external_reference
            HAVING COUNT(DISTINCT owner_name) > 1 
               OR COUNT(DISTINCT owner_email) > 1
               OR COUNT(DISTINCT owner_cpf) > 1
               OR COUNT(DISTINCT owner_phone) > 1
               OR COUNT(DISTINCT payment_status) > 1
        """)
        inconsistencies = db.execute(sql).fetchall()
        if inconsistencies:
            print("❌ Erro: Encontradas inconsistências nos dados de compra!")
            for inc in inconsistencies:
                print(f"Compra {inc.external_reference} tem dados inconsistentes")
            return False
            
        print("✅ Verificação de integridade concluída com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a verificação: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("\n=== Verificação de Integridade dos Dados ===\n")
    if verify_data_integrity():
        print("\n✨ Todos os dados estão íntegros e consistentes!")
    else:
        print("\n❌ Foram encontrados problemas na integridade dos dados!") 