import os
import logging
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify # Importe request e jsonify
from flask_mail import Mail, Message
import csv
import random
import requests
import json
import mercadopago # Importe a SDK do Mercado Pago

# Carrega as variáveis do ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# Configuração do Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Variável de controle para o e-mail de teste
email_test_sent = False

# Configuração do Flask-Mail usando variáveis de ambiente
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Pega a URL do webhook do Discord do .env
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Configuração do Mercado Pago
# Você precisará de suas credenciais de Produção e/ou Teste
# https://www.mercadopago.com.br/developers/panel/credentials
app.config['MP_ACCESS_TOKEN'] = os.getenv('MP_ACCESS_TOKEN') # Seu Access Token do Mercado Pago
sdk = mercadopago.SDK(app.config['MP_ACCESS_TOKEN'])

mail = Mail(app)

# Dicionário temporário para armazenar dados da compra enquanto o pagamento é processado.
# ATENÇÃO: Em um ambiente de produção, isso DEVERIA ser um banco de dados persistente!
# Formato: { 'payment_id_mercado_pago': { 'name': '', 'email': '', 'cpf': '', 'phone': '', 'quantity': 0, 'assigned_tokens': [], 'status': 'pending' } }
pending_payments_data = {}

# Carrega tokens do CSV
def load_tokens(filename="tokens.csv"):
    logging.info(f"✨ Iniciando carregamento de tokens do arquivo: {filename}")
    tokens = []
    try:
        with open(filename, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                if row:
                    tokens.append(row[0])
        logging.info(f"✅ Tokens carregados com sucesso! Total de {len(tokens)} tokens disponíveis.")
    except FileNotFoundError:
        logging.error(f"❌ Erro: Arquivo '{filename}' não encontrado. Certifique-se de que o arquivo 'tokens.csv' existe na raiz do projeto.")
    except Exception as e:
        logging.error(f"⚠️ Erro ao carregar tokens do CSV: {e}")
    return tokens

available_tokens = load_tokens()
used_tokens = set()

# Função para verificar o serviço de e-mail ao iniciar
def check_email_service():
    global email_test_sent
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

@app.route('/create_preference', methods=['POST'])
def create_preference():
    logging.info("🛒 Requisição POST recebida para '/create_preference' para criar preferência de pagamento.")
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    cpf = data.get('cpf')
    phone = data.get('phone')
    quantity = data.get('quantity')
    valor_unitario = 10.00 # Certifique-se que este valor está consistente com o frontend

    if not all([name, email, cpf, phone, quantity]):
        logging.warning("⚠️ Validação de dados para preferência de pagamento falhou: Campos obrigatórios ausentes.")
        return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios para gerar o pagamento!'}), 400

    if not isinstance(quantity, int) or quantity <= 0:
        logging.warning(f"⚠️ Validação de dados para preferência de pagamento falhou: Quantidade inválida recebida: {quantity}")
        return jsonify({'success': False, 'message': 'Quantidade inválida!'}), 400

    total_amount = float(quantity * valor_unitario)

    # Atribui os tokens temporariamente para esta compra
    # IMPORTANT: Estes tokens SÓ SERÃO MARCADO COMO USADOS DEFINITIVAMENTE APÓS O PAGAMENTO SER APROVADO VIA IPN
    assigned_tokens = []
    temp_available_for_purchase = list(set(available_tokens) - used_tokens)

    if len(temp_available_for_purchase) < quantity:
        logging.warning(f"⚠️ Não há tokens únicos suficientes disponíveis para criar a preferência ({quantity} solicitados).")
        return jsonify({'success': False, 'message': 'Não há tokens suficientes disponíveis para esta quantidade no momento.'}), 400

    # Seleciona tokens para esta preferência (ainda não marcados como usados globalmente)
    for _ in range(quantity):
        token = random.choice(temp_available_for_purchase)
        assigned_tokens.append(token)
        temp_available_for_purchase.remove(token) # Remove da lista temporária para evitar duplicidade NESTA preferência

    # Cria o item para o Mercado Pago
    item = {
        "title": f"Números da Sorte para Sorteio do Carro ({quantity} un.)",
        "quantity": 1, # Quantidade de "item" no Mercado Pago, não o número de números da sorte
        "unit_price": total_amount,
        "currency_id": "BRL",
        "picture_url": "https://example.com/ticket.png" # Substitua pela URL da sua imagem do bilhete
    }

    # Dados do pagador (para preencher automaticamente no MP)
    payer = {
        "name": name,
        "surname": "", # Mercado Pago geralmente usa apenas o nome
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

    # Gera um ID único para esta transação ANTES de chamar o Mercado Pago
    # Usaremos este ID para rastrear a compra pendente
    order_id = f"ORDER-{random.randint(100000, 999999)}"

    # Armazena os dados da compra em pending_payments_data, com status "pending"
    # Este 'order_id' será o 'external_reference' do Mercado Pago
    pending_payments_data[order_id] = {
        'name': name,
        'email': email,
        'cpf': cpf,
        'phone': phone,
        'quantity': quantity,
        'assigned_tokens': assigned_tokens,
        'status': 'pending', # Estado inicial da compra
        'total_amount': total_amount
    }
    logging.info(f"Dados da compra pendente armazenados para Order ID: {order_id}")

    # Cria a preferência de pagamento no Mercado Pago
    preference_data = {
        "items": [item],
        "payer": payer,
        "external_reference": order_id, # Usado para linkar o pagamento do MP com sua compra interna
        "notification_url": f"https://sorteio-production.up.railway.app/mercadopago_webhook", # Sua URL para receber notificações do MP
        "auto_return": "all", # Retorna sempre, independente do status
        "back_urls": {
            "success": f"https://sorteio-production.up.railway.app/payment_status?status=success&order_id={order_id}",
            "pending": f"https://sorteio-production.up.railway.app/payment_status?status=pending&order_id={order_id}",
            "failure": f"https://sorteio-production.up.railway.app/payment_status?status=failure&order_id={order_id}"
        }
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        payment_link = preference["init_point"] # Link para o checkout do Mercado Pago
        logging.info(f"Preferência de pagamento criada com sucesso. ID: {preference['id']}")
        return jsonify({'success': True, 'payment_link': payment_link, 'preference_id': preference['id']})

    except Exception as e:
        logging.error(f"❌ Erro ao criar preferência de pagamento no Mercado Pago: {e}")
        # Remove a compra pendente se a criação da preferência falhar
        if order_id in pending_payments_data:
            del pending_payments_data[order_id]
        return jsonify({'success': False, 'message': f'Erro ao iniciar pagamento: {str(e)}'}), 500

# Endpoint para receber notificações do Mercado Pago (IPN - Instant Payment Notification)
# ESTA É A PARTE CRÍTICA PARA CONFIRMAR O PAGAMENTO!
@app.route('/mercadopago_webhook', methods=['GET', 'POST'])
def mercadopago_webhook():
    logging.info("🔔 Notificação de Mercado Pago Webhook recebida!")
    if request.method == 'GET':
        # Mercado Pago faz um GET inicial para verificar o webhook
        logging.info(f"Webhook GET request: {request.args}")
        # Você deve retornar 200 OK para o MP validar o webhook
        return "OK", 200
    elif request.method == 'POST':
        notification_data = request.args # Dados da notificação geralmente vêm como query params
        # Alternativamente, pode vir no corpo para "merchant_orders" ou "payments"
        # notification_data = request.get_json() if request.is_json else request.form

        topic = notification_data.get('topic') # Ex: 'payment', 'merchant_order'
        resource_id = notification_data.get('id') # ID do recurso (pagamento, ordem, etc.)

        logging.info(f"Webhook POST request: Topic='{topic}', Resource ID='{resource_id}'")

        if topic == 'payment':
            # Detalhes do pagamento
            payment_info = sdk.payment().get(resource_id)
            payment_status = payment_info["response"]["status"]
            external_reference = payment_info["response"]["external_reference"] # Nosso order_id

            logging.info(f"Notificação de Pagamento - ID: {resource_id}, Status: {payment_status}, External Ref: {external_reference}")

            if external_reference in pending_payments_data:
                purchase_data = pending_payments_data[external_reference]
                if payment_status == 'approved':
                    if purchase_data['status'] == 'pending': # Evita processar múltiplas vezes
                        logging.info(f"✅ Pagamento APROVADO para Order ID: {external_reference}. Processando compra.")
                        # ATUALIZA O STATUS DA COMPRA
                        purchase_data['status'] = 'approved'

                        # ATRIBUI OS TOKENS DEFINITIVAMENTE (marca como usados)
                        for token in purchase_data['assigned_tokens']:
                            if token in available_tokens: # Verifica se o token ainda está disponível
                                used_tokens.add(token) # Marca como usado globalmente
                                available_tokens.remove(token) # Remove do pool de disponíveis
                                logging.info(f"Token '{token}' marcado como USADO para Order ID: {external_reference}.")
                            else:
                                logging.warning(f"⚠️ Token '{token}' (do pedido {external_reference}) não encontrado nos disponíveis ao aprovar o pagamento. Possível inconsistência ou uso prévio.")

                        # Envia e-mails de confirmação (cliente e admin)
                        customer_email_subject = "Detalhes da sua Compra Confirmada - Sorteio do Carro"
                        customer_email_body = f"""
                        Prezado(a) {purchase_data['name']},

                        Seu pagamento foi CONFIRMADO com sucesso!
                        Obrigado por participar do nosso sorteio!

                        Aqui estão os detalhes da sua compra:
                        Nome: {purchase_data['name']}
                        Email: {purchase_data['email']}
                        CPF: {purchase_data['cpf']}
                        Telefone: {purchase_data['phone']}
                        Quantidade de números da sorte: {purchase_data['quantity']}
                        Seus números da sorte: {', '.join(purchase_data['assigned_tokens'])}

                        Boa sorte!
                        """
                        admin_email_subject = f"✅ Compra Confirmada - Sorteio do Carro - {purchase_data['name']}"
                        admin_email_body = f"""
                        COMPRA CONFIRMADA!

                        Cliente: {purchase_data['name']}
                        Email do Cliente: {purchase_data['email']}
                        CPF: {purchase_data['cpf']}
                        Telefone: {purchase_data['phone']}
                        Quantidade de números comprados: {purchase_data['quantity']}
                        Tokens Atribuídos: {', '.join(purchase_data['assigned_tokens'])}
                        Status do Pagamento (MP): APROVADO
                        ID do Pagamento (MP): {resource_id}
                        """
                        try:
                            msg_customer = Message(customer_email_subject, recipients=[purchase_data['email']], body=customer_email_body)
                            mail.send(msg_customer)
                            logging.info(f"✅ E-mail de confirmação de compra APROVADA enviado para o cliente: {purchase_data['email']}.")

                            msg_admin = Message(admin_email_subject, recipients=[app.config['MAIL_DEFAULT_SENDER']], body=admin_email_body)
                            mail.send(msg_admin)
                            logging.info(f"✅ E-mail de notificação de compra APROVADA enviado para o administrador.")

                            discord_message = (
                                f"🎉 COMPRA CONFIRMADA! 🎉\n"
                                f"Cliente: **{purchase_data['name']}** ({purchase_data['email']})\n"
                                f"Comprou: **{purchase_data['quantity']}** números\n"
                                f"Total: **R${purchase_data['total_amount']:.2f}**\n"
                                f"Tokens: `{', '.join(purchase_data['assigned_tokens'])}`\n"
                                f"Status MP: APROVADO\n"
                                f"ID Pagamento MP: `{resource_id}`"
                            )
                            send_discord_notification(discord_message, color=3066993) # Cor verde de sucesso

                        except Exception as e:
                            logging.error(f"❌ Erro ao enviar e-mails/Discord de confirmação de compra APROVADA para {purchase_data['email']}. Erro: {e}")
                    else:
                        logging.info(f"ℹ️ Pagamento APROVADO para Order ID: {external_reference}, mas já processado anteriormente. Status: {purchase_data['status']}.")

                elif payment_status == 'rejected':
                    if purchase_data['status'] == 'pending':
                        logging.warning(f"❌ Pagamento REJEITADO para Order ID: {external_reference}. Não processando compra.")
                        purchase_data['status'] = 'rejected'
                        # Você pode querer liberar os tokens de volta para 'available_tokens' aqui
                        # ou lidar com a lógica de estoque de outra forma.
                        # Por simplicidade, não liberaremos aqui, mas em um sistema real, seria crucial.
                        discord_message = (
                            f"💔 PAGAMENTO REJEITADO! 💔\n"
                            f"Cliente: **{purchase_data['name']}** ({purchase_data['email']})\n"
                            f"Tentou comprar: **{purchase_data['quantity']}** números\n"
                            f"Total: **R${purchase_data['total_amount']:.2f}**\n"
                            f"Status MP: REJEITADO\n"
                            f"ID Pagamento MP: `{resource_id}`"
                        )
                        send_discord_notification(discord_message, color=15158332) # Cor vermelha de erro
                    else:
                        logging.info(f"ℹ️ Pagamento REJEITADO para Order ID: {external_reference}, mas já processado anteriormente. Status: {purchase_data['status']}.")
                elif payment_status == 'pending':
                    logging.info(f"⏳ Pagamento PENDENTE para Order ID: {external_reference}. Aguardando confirmação.")
                    purchase_data['status'] = 'pending'
                    # Nenhuma ação imediata além de atualizar o status interno
            else:
                logging.warning(f"⚠️ Notificação de pagamento para external_reference '{external_reference}' não encontrada em nossos registros pendentes.")
        # Sempre retorne 200 OK para o Mercado Pago, para que ele pare de reenviar a notificação
        return "OK", 200
    return "Method Not Allowed", 405 # Para outros métodos HTTP

# Rota para a página de status de pagamento (retorno do Mercado Pago)
@app.route('/payment_status')
def payment_status():
    status = request.args.get('status')
    order_id = request.args.get('order_id')
    preference_id = request.args.get('preference_id') # Adicional, pode vir em alguns fluxos

    logging.info(f"🌐 Cliente retornou da página de pagamento. Status: {status}, Order ID: {order_id}")

    if order_id and order_id in pending_payments_data:
        purchase_data = pending_payments_data[order_id]
        if purchase_data['status'] == 'approved':
            logging.info(f"Pagamento para Order ID '{order_id}' já está APROVADO. Redirecionando para sucesso.")
            # Redireciona para a página de sucesso com os tokens.
            return render_template('success.html', tokens=purchase_data['assigned_tokens'])
        elif purchase_data['status'] == 'pending':
            logging.info(f"Pagamento para Order ID '{order_id}' está PENDENTE. Exibindo mensagem ao usuário.")
            return render_template('payment_pending.html') # Crie este template
        elif purchase_data['status'] == 'rejected':
            logging.warning(f"Pagamento para Order ID '{order_id}' foi REJEITADO. Exibindo mensagem ao usuário.")
            return render_template('payment_rejected.html') # Crie este template
    else:
        logging.warning(f"Retorno de pagamento para Order ID '{order_id}' não encontrado ou inválido.")
        # Caso o order_id não seja encontrado, ou para status desconhecidos
        return render_template('payment_generic_status.html', status=status) # Crie este template genérico

@app.route('/success')
def success():
    # Esta rota agora pode ser acessada diretamente após o IPN confirmar o pagamento
    # (ou para onde `payment_status` redireciona quando aprovado)
    # Os tokens virão do `payment_status` ou via `purchase_data`
    tokens_json = request.args.get('tokens')
    tokens = []
    if tokens_json:
        try:
            tokens = json.loads(tokens_json)
        except json.JSONDecodeError:
            logging.error(f"Erro ao decodificar tokens JSON na página de sucesso: {tokens_json}")
    logging.info("✔️ Requisição recebida para a página de sucesso ('/success').")
    return render_template('success.html', tokens=tokens)


if __name__ == '__main__':
    # ... (suas verificações e logs)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)