# 🎰 Sistema de Sorteio de Carro

Sistema web para venda de números da sorte para sorteio de carro, com integração ao Mercado Pago para pagamentos.

## 🚀 Funcionalidades

- ✨ Interface moderna e responsiva
- 💳 Integração com Mercado Pago
- 📧 Notificações por e-mail automáticas
- 🔔 Notificações no Discord
- 🎫 Gerenciamento de números da sorte
- 📱 Layout adaptativo para mobile
- 🖨️ Opção de impressão dos números

## 🛠️ Tecnologias Utilizadas

- Python 3.x
- Flask (Framework Web)
- SQLAlchemy (ORM)
- PostgreSQL (Banco de Dados)
- Mercado Pago SDK
- Flask-Mail
- HTML/CSS
- Vercel (Deploy)

## ⚙️ Configuração do Ambiente

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/Sorteio.git
cd Sorteio
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente (.env):
```env
# Banco de Dados
DATABASE_URL=postgresql://user:password@localhost:5432/sorteio

# Mercado Pago
MP_ACCESS_TOKEN=seu_token_aqui

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=seu_email@gmail.com
MAIL_PASSWORD=sua_senha_app
MAIL_DEFAULT_SENDER=seu_email@gmail.com

# Discord
DISCORD_WEBHOOK_URL=sua_url_webhook

# Aplicação
BASE_URL=https://seu-dominio.com
```

## 🗃️ Estrutura do Banco de Dados

O sistema utiliza uma tabela principal:

### Tabela: tokens
- `id`: ID único do token
- `number`: Número da sorte
- `is_used`: Status de uso
- `owner_name`: Nome do comprador
- `owner_email`: Email do comprador
- `owner_cpf`: CPF do comprador
- `owner_phone`: Telefone do comprador
- `payment_id`: ID do pagamento (Mercado Pago)
- `payment_status`: Status do pagamento
- `external_reference`: Referência externa
- `purchase_date`: Data da compra
- `total_amount`: Valor pago

## 📋 Scripts de Utilidade

- `reset_db.py`: Reseta o banco de dados e carrega tokens iniciais
- `check_db.py`: Verifica integridade dos dados
- `verify_data_integrity.py`: Validação completa dos dados

## 🔄 Fluxo de Pagamento

1. Cliente seleciona quantidade de números
2. Sistema reserva números disponíveis
3. Integração com Mercado Pago gera pagamento
4. Webhook recebe confirmação de pagamento
5. Sistema envia emails e notificações
6. Números são marcados como vendidos

## 📱 Endpoints da API

- `GET /`: Página inicial
- `POST /create_preference`: Cria preferência de pagamento
- `POST /mercadopago_webhook`: Webhook do Mercado Pago
- `GET /payment_status`: Status do pagamento
- `GET /test_notifications`: Teste de notificações

## 🔍 Monitoramento

O sistema inclui logs detalhados para:
- Transações de pagamento
- Envio de emails
- Notificações Discord
- Operações no banco de dados
- Webhooks recebidos

## 🚨 Tratamento de Erros

- Validação de dados de entrada
- Tratamento de falhas de pagamento
- Backup de dados importantes
- Logs de erros detalhados
- Notificações de falhas

## 🔐 Segurança

- Validação de webhooks
- Proteção contra duplicidade
- Sanitização de inputs
- Controle de acesso
- Backup automático

## 📦 Deploy

O sistema está configurado para deploy na Vercel:
- Arquivo `vercel.json` com configurações
- Suporte a serverless functions
- Configuração de rotas
- Variáveis de ambiente

## 🤝 Contribuição

1. Faça o fork do projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add: nova funcionalidade'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes. 