import requests
import json
import time
from datetime import datetime
import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL base da aplicação
BASE_URL = "http://localhost:5000"

def test_create_preference():
    """Testa a criação de uma preferência de pagamento"""
    logger.info("\n=== Testando criação de preferência ===")
    
    # Dados do teste
    test_data = {
        "name": "Teste Usuário",
        "email": "teste@teste.com",
        "cpf": "12345678900",
        "phone": "11999999999",
        "quantity": 2
    }
    
    try:
        # Faz a requisição
        response = requests.post(
            f"{BASE_URL}/create_preference",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Verifica o status da resposta
        assert response.status_code == 200, f"Erro na requisição: {response.status_code}"
        
        # Verifica o conteúdo da resposta
        data = response.json()
        logger.info(f"Resposta da API: {data}")
        
        assert "payment_link" in data, "Link de pagamento não encontrado na resposta"
        assert "order_id" in data, "ID do pedido não encontrado na resposta"
        
        logger.info("✅ Teste de criação de preferência passou!")
        logger.info(f"Link de pagamento: {data['payment_link']}")
        logger.info(f"ID do pedido: {data['order_id']}")
        
        return data
        
    except Exception as e:
        logger.error(f"❌ Erro no teste de criação de preferência: {str(e)}")
        raise

def test_payment_status():
    """Testa a verificação de status de pagamento"""
    logger.info("\n=== Testando verificação de status de pagamento ===")
    
    try:
        # Primeiro cria uma preferência para ter um order_id
        preference_data = test_create_preference()
        order_id = preference_data["order_id"]
        
        # Aguarda um pouco para simular o processamento
        time.sleep(2)
        
        # Testa diferentes status
        test_statuses = ["approved", "rejected", "cancelled", "refunded", "pending"]
        
        for status in test_statuses:
            # Faz a requisição
            response = requests.get(
                f"{BASE_URL}/payment_status",
                params={
                    "preference_id": order_id,
                    "external_reference": order_id,
                    "status": status
                }
            )
            
            # Verifica o status da resposta
            assert response.status_code == 200, f"Erro na requisição: {response.status_code}"
            
            # Verifica o conteúdo da resposta
            data = response.json()
            assert "message" in data, "Mensagem não encontrada na resposta"
            
            logger.info(f"✅ Teste de status '{status}' passou!")
            logger.info(f"Mensagem: {data['message']}")
            
    except Exception as e:
        logger.error(f"❌ Erro no teste de status de pagamento: {str(e)}")
        raise

def test_my_purchases():
    """Testa a visualização de compras"""
    logger.info("\n=== Testando visualização de compras ===")
    
    try:
        # Faz a requisição
        response = requests.get(f"{BASE_URL}/my_purchases")
        
        # Verifica o status da resposta
        assert response.status_code == 200, f"Erro na requisição: {response.status_code}"
        
        logger.info("✅ Teste de visualização de compras passou!")
        
    except Exception as e:
        logger.error(f"❌ Erro no teste de visualização de compras: {str(e)}")
        raise

def run_all_tests():
    """Executa todos os testes"""
    logger.info("\n=== Iniciando testes locais ===")
    
    try:
        # Testa criação de preferência
        test_create_preference()
        
        # Testa verificação de status
        test_payment_status()
        
        # Testa visualização de compras
        test_my_purchases()
        
        logger.info("\n✅ Todos os testes passaram com sucesso!")
        
    except Exception as e:
        logger.error(f"\n❌ Alguns testes falharam: {str(e)}")
        raise

if __name__ == "__main__":
    run_all_tests() 