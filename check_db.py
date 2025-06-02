from database import SessionLocal, Token

def check_tokens_and_users():
    db = SessionLocal()
    try:
        print("\n=== Tokens Vendidos e Seus Proprietários ===")
        # Busca todos os tokens vendidos
        tokens = db.query(Token).filter_by(is_used=True).all()
        
        if tokens:
            current_user = None
            for token in tokens:
                if current_user != token.owner_email:
                    # Imprime informações do usuário quando muda
                    print(f"\nComprador: {token.owner_name}")
                    print(f"Email: {token.owner_email}")
                    print(f"CPF: {token.owner_cpf}")
                    print(f"Telefone: {token.owner_phone}")
                    print(f"Status do Pagamento: {token.payment_status}")
                    print("Números da Sorte:")
                    current_user = token.owner_email
                print(f"- {token.number}")
        else:
            print("Nenhum token foi vendido ainda!")
            
        # Estatísticas gerais
        total_tokens = db.query(Token).count()
        used_tokens = db.query(Token).filter_by(is_used=True).count()
        total_users = db.query(Token.owner_email).filter(Token.is_used == True).distinct().count()
        
        print(f"\n=== Estatísticas Gerais ===")
        print(f"Total de tokens: {total_tokens}")
        print(f"Tokens vendidos: {used_tokens}")
        print(f"Tokens disponíveis: {total_tokens - used_tokens}")
        print(f"Total de compradores: {total_users}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_tokens_and_users() 