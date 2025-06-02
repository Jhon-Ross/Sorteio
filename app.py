import os
import logging
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from flask_mail import Mail, Message
import random
import requests
import json
import mercadopago
from database import SessionLocal, Token
import traceback
from datetime import datetime

# Carrega as variáveis do ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# Configuração do Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Variável de controle para o e-mail de teste
email_test_sent = False

# Configuração do Flask-Mail usando variáveis de ambiente
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', '')

# Pega a URL do webhook do Discord do .env
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# URL base da aplicação (Vercel)
BASE_URL = os.getenv('BASE_URL', 'https://sorteio-gray.vercel.app')
if BASE_URL.startswith('postgresql://'):
    logging.warning("⚠️ BASE_URL está configurada incorretamente com uma string de conexão de banco de dados!")
    BASE_URL = 'https://sorteio-gray.vercel.app'  # Fallback para URL padrão

# Configuração do Mercado Pago
mp_token = os.getenv('MP_ACCESS_TOKEN')
if mp_token:
    app.config['MP_ACCESS_TOKEN'] = mp_token
    sdk = mercadopago.SDK(mp_token)
else:
    logging.warning("⚠️ MP_ACCESS_TOKEN não configurado. Funcionalidades de pagamento não estarão disponíveis.")
    sdk = None

mail = Mail(app)

# Função para verificar o serviço de e-mail ao iniciar
def check_email_service():
    global email_test_sent
    
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD') or not app.config.get('MAIL_DEFAULT_SENDER'):
        logging.warning("⚠️ Configurações de e-mail não estão completas. Pulando verificação de e-mail.")
        return False
    
    if email_test_sent and app.debug:
        logging.info("📧 E-mail de verificação já foi enviado e estamos em modo debug, ignorando novo envio.")
        return True

    sender_email = app.config['MAIL_DEFAULT_SENDER']
    logging.info(f"🚀 Iniciando verificação do serviço de e-mail para: {sender_email}")
    try:
        with app.app_context():
            msg = Message(subject="Verificação de E-mail - Sorteio do Carro",
                          recipients=[sender_email],
                          body="Este é um e-mail de teste para verificar a configuração do seu serviço de e-mail para o Sorteio do Carro. Se você recebeu esta mensagem, o serviço está funcionando corretamente.")
            mail.send(msg)
        logging.info(f"✅ E-mail de verificação enviado com sucesso para: {sender_email}.")
        email_test_sent = True
        return True
    except Exception as e:
        logging.error(f"❌ Falha na verificação do serviço de e-mail. Erro: {e}")
        logging.warning("⚠️ Verifique suas configurações de e-mail no arquivo .env (MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD) e as permissões da sua conta (ex: Senha de App no Gmail).")
        return False

# Função para enviar mensagem para o Discord Webhook
def send_discord_notification(message, color=None):
    if not DISCORD_WEBHOOK_URL:
        logging.warning("⚠️ URL do webhook do Discord não configurada no .env. Ignorando notificação.")
        return

    headers = {'Content-Type': 'application/json'}
    payload = {
        "content": None,
        "embeds": [
            {
                "description": message,
                "color": color if color else 3066993
            }
        ]
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        logging.info("🔔 Mensagem de status enviada para o Discord com sucesso.")
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Erro ao enviar mensagem para o Discord Webhook: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"❌ Erro de codificação JSON para o Discord Webhook: {e}")

@app.route('/')
def index():
    logging.info("🌐 Requisição recebida para a página inicial ('/').")
    return render_template('index.html')

@app.route('/health')
def health():
    """Endpoint de health check para Railway e outros serviços"""
    try:
        db = SessionLocal()
        total_tokens = db.query(Token).count()
        used_tokens = db.query(Token).filter_by(is_used=True).count()
        available_tokens = total_tokens - used_tokens
        return {'status': 'ok', 'tokens_available': available_tokens, 'tokens_used': used_tokens}, 200
    except Exception as e:
        return {'status': 'error', 'error': str(e)}, 500

@app.errorhandler(500)
def handle_500_error(e):
    logging.error(f"Erro 500: {str(e)}")
    logging.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({
        'success': False,
        'message': 'Erro interno do servidor',
        'error': str(e),
        'traceback': traceback.format_exc()
    }), 500

@app.route('/create_preference', methods=['POST'])
def create_preference():
    logging.info("🛒 Requisição POST recebida para '/create_preference' para criar preferência de pagamento.")
    try:
        data = request.get_json()
        if data is None:
            logging.error("❌ Dados JSON não encontrados no request")
            return jsonify({'success': False, 'message': 'Dados JSON não encontrados'}), 400
            
        logging.info(f"Dados recebidos: {data}")
        
        name = data.get('name')
        email = data.get('email')
        cpf = data.get('cpf')
        phone = data.get('phone')
        quantity = data.get('quantity')
        
        # Log dos dados recebidos
        logging.info(f"Nome: {name}")
        logging.info(f"Email: {email}")
        logging.info(f"CPF: {cpf}")
        logging.info(f"Telefone: {phone}")
        logging.info(f"Quantidade: {quantity}")
        
        valor_unitario = 10.00

        if not all([name, email, cpf, phone, quantity]):
            logging.warning("⚠️ Validação de dados para preferência de pagamento falhou: Campos obrigatórios ausentes.")
            return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios para gerar o pagamento!'}), 400

        if not isinstance(quantity, int) or quantity <= 0:
            logging.warning(f"⚠️ Validação de dados para preferência de pagamento falhou: Quantidade inválida recebida: {quantity}")
            return jsonify({'success': False, 'message': 'Quantidade inválida!'}), 400

        total_amount = float(quantity * valor_unitario)
        logging.info(f"Valor total calculado: R${total_amount}")

        # Verifica disponibilidade de tokens no banco de dados
        try:
            db = SessionLocal()
            available_tokens = db.query(Token).filter_by(is_used=False).count()
            logging.info(f"Tokens disponíveis no banco: {available_tokens}")

            if available_tokens < quantity:
                logging.warning(f"⚠️ Não há tokens únicos suficientes disponíveis para criar a preferência ({quantity} solicitados).")
                return jsonify({'success': False, 'message': 'Não há tokens suficientes disponíveis para esta quantidade no momento.'}), 400

            # Seleciona tokens aleatórios não utilizados
            available_tokens = db.query(Token).filter_by(is_used=False).all()
            selected_tokens = random.sample(available_tokens, quantity)
            logging.info(f"Tokens selecionados: {[token.number for token in selected_tokens]}")

            # Gera um ID único para esta transação
            order_id = f"ORDER-{random.randint(100000, 999999)}"
            logging.info(f"Order ID gerado: {order_id}")

            # Marca os tokens como utilizados e adiciona informações do comprador
            for token in selected_tokens:
                token.is_used = True
                token.owner_name = name
                token.owner_email = email
                token.owner_cpf = cpf
                token.owner_phone = phone
                token.external_reference = order_id
                token.payment_status = 'pending'
                token.total_amount = total_amount / quantity  # Divide o valor total pela quantidade
                token.purchase_date = datetime.utcnow()

            # Cria o item para o Mercado Pago
            item = {
                "title": f"Números da Sorte para Sorteio do Carro ({quantity} un.)",
                "quantity": 1,
                "unit_price": total_amount,
                "currency_id": "BRL",
                "picture_url": "https://example.com/ticket.png"
            }
            logging.info(f"Item criado para MP: {item}")

            # Dados do pagador
            payer = {
                "name": name,
                "surname": "",
                "email": email,
                "identification": {
                    "type": "CPF",
                    "number": cpf
                },
                "phone": {
                    "area_code": phone[:2] if len(phone) >= 10 else "",
                    "number": phone[2:] if len(phone) >= 10 else phone
                }
            }
            logging.info(f"Dados do pagador: {payer}")

            # Cria a preferência de pagamento no Mercado Pago
            preference_data = {
                "items": [item],
                "payer": payer,
                "external_reference": order_id,
                "notification_url": f"{BASE_URL}/mercadopago_webhook",
                "auto_return": "all",
                "back_urls": {
                    "success": f"{BASE_URL}/payment_status?status=success&order_id={order_id}",
                    "pending": f"{BASE_URL}/payment_status?status=pending&order_id={order_id}",
                    "failure": f"{BASE_URL}/payment_status?status=failure&order_id={order_id}"
                }
            }
            logging.info(f"Dados da preferência MP: {preference_data}")

            if not sdk:
                logging.error("❌ SDK do Mercado Pago não configurado!")
                db.rollback()
                return jsonify({'success': False, 'message': 'Serviço de pagamento temporariamente indisponível.'}), 503
                
            logging.info("Criando preferência no Mercado Pago...")
            preference_response = sdk.preference().create(preference_data)
            preference = preference_response["response"]
            payment_link = preference["init_point"]

            # Commit as alterações no banco de dados
            db.commit()
            logging.info(f"Preferência de pagamento criada com sucesso. ID: {preference['id']}")
            return jsonify({'success': True, 'payment_link': payment_link, 'preference_id': preference['id']})

        except Exception as e:
            if db:
                db.rollback()
            logging.error(f"❌ Erro ao criar preferência de pagamento: {str(e)}")
            logging.error(f"Traceback completo: {traceback.format_exc()}")
            return jsonify({'success': False, 'message': f'Erro ao iniciar pagamento: {str(e)}'}), 500
        finally:
            if db:
                db.close()
    except Exception as e:
        logging.error(f"❌ Erro geral na rota create_preference: {str(e)}")
        logging.error(f"Traceback completo: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'Erro ao processar requisição: {str(e)}'}), 500

@app.route('/mercadopago_webhook', methods=['GET', 'POST'])
def mercadopago_webhook():
    print("=== WEBHOOK RECEBIDO ===")
    print(f"Método: {request.method}")
    print(f"Headers: {request.headers}")
    print(f"Args: {request.args}")
    print(f"Data: {request.get_data(as_text=True)}")
    
    if request.method == 'GET':
        print(f"Webhook GET request: {request.args}")
        return "OK", 200
    elif request.method == 'POST':
        try:
            print("=== PROCESSANDO WEBHOOK POST ===")
            notification_data = request.args
            
            # Verifica os dois formatos possíveis de notificação
            topic = notification_data.get('topic')
            notification_type = notification_data.get('type')
            
            # Pega o ID do recurso nos dois formatos possíveis
            resource_id = notification_data.get('id') or notification_data.get('data.id')

            print(f"Topic: {topic}, Type: {notification_type}, Resource ID: {resource_id}")

            # Verifica se é uma notificação de pagamento em qualquer um dos formatos
            is_payment = topic == 'payment' or notification_type == 'payment'
            
            if is_payment and resource_id:
                print("=== PAGAMENTO DETECTADO ===")
                if not sdk:
                    print("ERRO: SDK do Mercado Pago não configurado")
                    return "OK", 200
                    
                print("Buscando informações do pagamento...")
                payment_info = sdk.payment().get(resource_id)
                print(f"Info do pagamento: {payment_info}")
                
                payment_status = payment_info["response"]["status"]
                external_reference = payment_info["response"]["external_reference"]

                print(f"Status: {payment_status}, Ref: {external_reference}")

                db = SessionLocal()
                try:
                    print("Buscando tokens no banco...")
                    tokens = db.query(Token).filter_by(external_reference=external_reference).all()
                    print(f"Tokens encontrados: {len(tokens)}")
                    
                    if tokens:
                        if payment_status == 'approved':
                            print("=== PAGAMENTO APROVADO ===")
                            for token in tokens:
                                token.payment_status = 'approved'
                                token.payment_id = resource_id

                            token_numbers = [token.number for token in tokens]
                            first_token = tokens[0]
                            
                            print(f"Preparando e-mails para {first_token.owner_email}")
                            
                            # Verificar configurações de e-mail
                            print("Verificando config de e-mail...")
                            mail_config = {
                                'MAIL_SERVER': app.config.get('MAIL_SERVER'),
                                'MAIL_PORT': app.config.get('MAIL_PORT'),
                                'MAIL_USE_TLS': app.config.get('MAIL_USE_TLS'),
                                'MAIL_USERNAME': app.config.get('MAIL_USERNAME'),
                                'MAIL_DEFAULT_SENDER': app.config.get('MAIL_DEFAULT_SENDER')
                            }
                            print(f"Config e-mail: {mail_config}")
                            
                            try:
                                print("=== ENVIANDO E-MAILS ===")
                                # E-mail para o administrador
                                admin_email_subject = f"✅ Compra Confirmada - Sorteio do Carro - {first_token.owner_name}"
                                admin_email_body = f"""
                                COMPRA CONFIRMADA!

                                Cliente: {first_token.owner_name}
                                Email do Cliente: {first_token.owner_email}
                                CPF: {first_token.owner_cpf}
                                Telefone: {first_token.owner_phone}
                                Quantidade de números comprados: {len(tokens)}
                                Tokens Atribuídos: {', '.join(token_numbers)}
                                Status do Pagamento (MP): APROVADO
                                ID do Pagamento (MP): {resource_id}
                                """
                                
                                print("Enviando e-mail admin...")
                                msg_admin = Message(
                                    subject=admin_email_subject,
                                    recipients=[app.config['MAIL_DEFAULT_SENDER']],
                                    body=admin_email_body
                                )
                                mail.send(msg_admin)
                                print("E-mail admin enviado!")
                                
                                # E-mail para o cliente
                                customer_email_subject = "🎉 Parabéns! Sua Compra foi Confirmada - Sorteio do Carro"
                                customer_email_body = f"""
                                Parabéns, {first_token.owner_name}! 🎉

                                Seu pagamento foi confirmado com sucesso e seus números da sorte já estão reservados! 

                                🎫 Seus números da sorte são:
                                {', '.join(token_numbers)}

                                Guarde bem esses números! Eles são sua chance de ganhar um carro 0km. 🚗✨
                                O sorteio será realizado pela Loteria Federal e o resultado será divulgado em nossas redes sociais.

                                Fique atento e boa sorte! 🍀

                                Atenciosamente,
                                Equipe do Sorteio
                                """
                                
                                print(f"Enviando e-mail cliente: {first_token.owner_email}")
                                msg_customer = Message(
                                    subject=customer_email_subject,
                                    recipients=[first_token.owner_email],
                                    body=customer_email_body
                                )
                                mail.send(msg_customer)
                                print("E-mail cliente enviado!")
                                
                            except Exception as e:
                                print(f"ERRO AO ENVIAR E-MAILS: {str(e)}")
                                error_message = f"⚠️ ERRO AO ENVIAR E-MAILS!\n\nCliente: {first_token.owner_name}\nErro: {str(e)}"
                                send_discord_notification(error_message, color=15158332)
                            
                            # Notificação Discord
                            try:
                                print("Enviando notificação Discord...")
                                discord_message = (
                                    f"🎰 **NOVA VENDA CONFIRMADA!** 🎰\n\n"
                                    f"**Detalhes da Compra:**\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"🎫 Quantidade: **{len(tokens)} números**\n"
                                    f"💰 Valor Total: **R$ {sum([t.total_amount for t in tokens]):.2f}**\n"
                                    f"🎟️ Números da Sorte:\n`{', '.join(token_numbers)}`\n\n"
                                    f"**Informações do Comprador:**\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"👤 Nome: **{first_token.owner_name}**\n"
                                    f"📧 E-mail: `{first_token.owner_email}`\n"
                                    f"📱 Telefone: `{first_token.owner_phone}`\n\n"
                                    f"**Status da Transação:**\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"✅ Situação: **PAGAMENTO APROVADO**\n"
                                    f"🔍 ID da Transação: `{resource_id}`\n"
                                    f"⏰ Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                                )
                                send_discord_notification(discord_message, color=3066993)
                                print("Discord enviado!")
                            except Exception as e:
                                print(f"ERRO DISCORD: {str(e)}")
                            
                            db.commit()
                            print("=== PROCESSO FINALIZADO COM SUCESSO ===")
                        else:
                            print(f"Status não aprovado: {payment_status}")
                    else:
                        print(f"Nenhum token encontrado para ref: {external_reference}")
                except Exception as e:
                    db.rollback()
                    print(f"ERRO NO BANCO: {str(e)}")
                finally:
                    db.close()
        except Exception as e:
            print(f"ERRO GERAL: {str(e)}")
            
        return "OK", 200
    return "Method Not Allowed", 405

@app.route('/payment_status')
def payment_status():
    status = request.args.get('status')
    order_id = request.args.get('order_id')
    collection_status = request.args.get('collection_status')
    payment_id = request.args.get('payment_id')
    external_reference = request.args.get('external_reference')

    print("=== CLIENTE RETORNOU DO PAGAMENTO ===")
    print(f"Status: {status}")
    print(f"Order ID: {order_id}")
    print(f"Collection Status: {collection_status}")
    print(f"Payment ID: {payment_id}")
    print(f"External Reference: {external_reference}")

    # Usa order_id ou external_reference (dependendo de qual está disponível)
    reference = order_id or external_reference
    
    if reference:
        db = SessionLocal()
        try:
            print(f"Buscando tokens para referência: {reference}")
            # Busca o primeiro token da compra para verificar o status
            token = db.query(Token).filter_by(external_reference=reference).first()
            if token:
                print(f"Token encontrado: {token.number}")
                # Verifica aprovação em qualquer um dos formatos possíveis
                is_approved = (
                    collection_status == 'approved' or 
                    status == 'approved' or 
                    token.payment_status == 'approved'
                )
                
                is_rejected = (
                    collection_status == 'rejected' or 
                    status == 'rejected' or 
                    token.payment_status == 'rejected'
                )

                if is_approved:
                    print("=== PAGAMENTO APROVADO ===")
                    # Atualiza o status no banco se necessário
                    if token.payment_status != 'approved':
                        print("Atualizando status no banco...")
                        tokens = db.query(Token).filter_by(external_reference=reference).all()
                        for t in tokens:
                            t.payment_status = 'approved'
                            t.payment_id = payment_id
                        db.commit()
                        print("Status atualizado com sucesso!")
                        
                    # Busca todos os tokens desta compra
                    tokens = db.query(Token).filter_by(external_reference=reference).all()
                    token_numbers = [t.number for t in tokens]
                    print(f"Números da sorte: {token_numbers}")
                    return render_template('success.html', tokens=token_numbers)
                elif is_rejected:
                    print("=== PAGAMENTO REJEITADO ===")
                    return render_template('payment_rejected.html')
                else:
                    print("=== PAGAMENTO PENDENTE ===")
                    return render_template('payment_pending.html')
            else:
                print(f"⚠️ Nenhum token encontrado para referência: {reference}")
                return render_template('payment_generic_status.html', status=status)
        finally:
            db.close()

    print("⚠️ Nenhuma referência de pedido encontrada")
    return render_template('payment_generic_status.html', status=status)

@app.route('/success')
def success():
    tokens_json = request.args.get('tokens')
    tokens = []
    if tokens_json:
        try:
            tokens = json.loads(tokens_json)
        except json.JSONDecodeError:
            logging.error(f"Erro ao decodificar tokens JSON na página de sucesso: {tokens_json}")
    logging.info("✔️ Requisição recebida para a página de sucesso ('/success').")
    return render_template('success.html', tokens=tokens)

@app.route('/test_notifications')
def test_notifications():
    try:
        logging.info("🧪 Iniciando teste de notificações...")
        results = {
            'discord': False,
            'admin_email': False,
            'customer_email': False
        }
        
        # Teste do Discord
        try:
            discord_message = (
                f"🧪 TESTE DE NOTIFICAÇÃO! 🧪\n\n"
                f"Se você está vendo esta mensagem, o webhook do Discord está funcionando corretamente!\n"
                f"Hora do teste: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )
            send_discord_notification(discord_message, color=3066993)
            results['discord'] = True
            logging.info("✅ Teste do Discord enviado com sucesso!")
        except Exception as e:
            logging.error(f"❌ Erro no teste do Discord: {str(e)}")
        
        # Teste de E-mail para o Admin
        try:
            test_subject = "🧪 Teste de E-mail Admin - Sorteio do Carro"
            test_body = f"""
Olá! Este é um e-mail de teste para o ADMINISTRADOR.

Se você está recebendo este e-mail, significa que o sistema de envio de e-mails para o admin está funcionando corretamente!

Hora do teste: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

Atenciosamente,
Sistema de Teste
"""
            msg_admin = Message(
                test_subject,
                recipients=[app.config['MAIL_DEFAULT_SENDER']],
                body=test_body
            )
            mail.send(msg_admin)
            results['admin_email'] = True
            logging.info("✅ Teste de e-mail admin enviado com sucesso!")
        except Exception as e:
            logging.error(f"❌ Erro no teste de e-mail admin: {str(e)}")

        # Teste de E-mail de Confirmação para Cliente
        try:
            customer_email = request.args.get('email', app.config['MAIL_DEFAULT_SENDER'])
            customer_subject = "🎉 Teste - Confirmação de Pagamento - Sorteio do Carro"
            customer_body = f"""
Parabéns, Cliente Teste! 🎉

Este é um e-mail de teste do sistema de confirmação de pagamento.
Se você está recebendo este e-mail, significa que o sistema de envio de confirmação está funcionando corretamente!

🎫 Seus números da sorte (exemplo) são:
T123, T456, T789

Guarde bem esses números! Eles são sua chance de ganhar um carro 0km. 🚗✨
O sorteio será realizado pela Loteria Federal e o resultado será divulgado em nossas redes sociais.

Hora do teste: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

Fique atento e boa sorte! 🍀

Atenciosamente,
Equipe do Sorteio
"""
            msg_customer = Message(
                subject=customer_subject,
                recipients=[customer_email],
                body=customer_body,
                sender=app.config['MAIL_DEFAULT_SENDER']
            )
            mail.send(msg_customer)
            results['customer_email'] = True
            logging.info(f"✅ Teste de e-mail cliente enviado com sucesso para {customer_email}!")
        except Exception as e:
            logging.error(f"❌ Erro no teste de e-mail cliente: {str(e)}")
        
        # Prepara a resposta
        success = all(results.values())
        message = "Status dos testes:\n"
        message += f"- Discord: {'✅' if results['discord'] else '❌'}\n"
        message += f"- E-mail Admin: {'✅' if results['admin_email'] else '❌'}\n"
        message += f"- E-mail Cliente: {'✅' if results['customer_email'] else '❌'}"
        
        return jsonify({
            'success': success,
            'results': results,
            'message': message
        })
        
    except Exception as e:
        logging.error(f"❌ Erro geral no teste de notificações: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro ao executar testes de notificação.'
        }), 500

if __name__ == '__main__':
    logging.info("🚀 Iniciando a aplicação Flask...")
    logging.info("🛡️ Realizando verificações de segurança da aplicação...")
    
    # Verifica serviço de e-mail
    if check_email_service():
        discord_message = "🚀 Aplicação Flask iniciada com sucesso! Todos os serviços estão operacionais."
        send_discord_notification(discord_message, color=3066993)
    
    # Configurações de produção
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)