import os
import logging
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from flask_mail import Mail, Message
import random
import requests
import json
import mercadopago
import psycopg2

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

# Configuração do banco de dados PostgreSQL
DATABASE_URL = os.getenv('POSTGRES_URL')

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logging.error(f"❌ Erro ao conectar ao banco de dados: {e}")
        raise

def contar_tokens_disponiveis_db():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(id) FROM Tokens WHERE disponivel = TRUE;")
        count = cur.fetchone()[0]
        return count
    finally:
        cur.close()
        conn.close()

def selecionar_tokens_aleatorios_db(quantidade):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute(
            "SELECT id, numero_token FROM Tokens WHERE disponivel = TRUE ORDER BY RANDOM() LIMIT %s;",
            (quantidade,)
        )
        tokens_selecionados = cur.fetchall()
        return tokens_selecionados
    finally:
        cur.close()
        conn.close()

# Função robusta para configurar Flask-Mail
mail = None
def configure_mail(app):
    try:
        required = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USE_TLS', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER']
        for key in required:
            if not app.config.get(key):
                raise ValueError(f"Variável de ambiente obrigatória ausente: {key}")
        return Mail(app)
    except Exception as e:
        logging.error(f"❌ Erro ao configurar Flask-Mail: {e}")
        return None

mail = configure_mail(app)

# Função robusta para verificar serviço de e-mail

def check_email_service():
    global email_test_sent
    if email_test_sent:
        logging.info("📧 E-mail de verificação já foi enviado.")
        return True
    if not mail:
        logging.error("❌ Serviço de e-mail não configurado corretamente.")
        return False
    sender_email = app.config.get('MAIL_DEFAULT_SENDER')
    if not sender_email:
        logging.error("❌ MAIL_DEFAULT_SENDER não configurado.")
        return False
    try:
        with app.app_context():
            msg = Message(subject="Verificação de E-mail - Sorteio do Carro",
                          recipients=[sender_email],
                          body="Este é um e-mail de teste para verificar a configuração do seu serviço de e-mail para o Sorteio do Carro.")
            mail.send(msg)
        logging.info(f"✅ E-mail de verificação enviado com sucesso para: {sender_email}.")
        email_test_sent = True
        return True
    except Exception as e:
        logging.error(f"❌ Falha na verificação do serviço de e-mail. Erro: {e}")
        return False

# Inicialização do Mercado Pago SDK de forma segura
def get_mp_sdk():
    access_token = app.config.get('MP_ACCESS_TOKEN')
    if not access_token:
        logging.error('❌ MP_ACCESS_TOKEN não configurado!')
        return None
    try:
        return mercadopago.SDK(access_token)
    except Exception as e:
        logging.error(f'❌ Erro ao inicializar Mercado Pago SDK: {e}')
        return None

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
    logging.info("🛒 Requisição POST recebida para '/create_preference'.")
    data = request.get_json()
    nome = data.get('name')
    email = data.get('email')
    cpf = data.get('cpf')
    phone = data.get('phone')
    quantity = data.get('quantity')
    valor_unitario = 10.00

    if not all([nome, email, cpf, phone, quantity]):
        logging.warning("⚠️ Validação falhou: Campos obrigatórios ausentes.")
        return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios!'}), 400

    if not isinstance(quantity, int) or not (1 <= quantity <= 2500):
        logging.warning(f"⚠️ Validação falhou: Quantidade inválida: {quantity}")
        return jsonify({'success': False, 'message': 'Quantidade inválida!'}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        conn.autocommit = False

        cur.execute("SELECT COUNT(id) FROM Tokens WHERE disponivel = TRUE;")
        tokens_disponiveis_count = cur.fetchone()['count']
        if tokens_disponiveis_count < quantity:
            conn.rollback()
            logging.warning(f"⚠️ Tokens insuficientes. Solicitados: {quantity}, Disponíveis: {tokens_disponiveis_count}")
            return jsonify({'success': False, 'message': 'Não há tokens suficientes disponíveis no momento.'}), 400

        cur.execute(
            "SELECT id, numero_token FROM Tokens WHERE disponivel = TRUE ORDER BY RANDOM() LIMIT %s FOR UPDATE;",
            (quantity,)
        )
        tokens_selecionados_rows = cur.fetchall()
        if len(tokens_selecionados_rows) < quantity:
            conn.rollback()
            logging.warning(f"⚠️ Não foi possível selecionar/reservar tokens suficientes. Solicitados: {quantity}, Selecionados: {len(tokens_selecionados_rows)}")
            return jsonify({'success': False, 'message': 'Não foi possível reservar os tokens necessários. Tente novamente.'}), 500

        assigned_token_ids = [str(row['id']) for row in tokens_selecionados_rows]
        assigned_token_numeros = [row['numero_token'] for row in tokens_selecionados_rows]
        order_id_interno = f"SORTEIO-{random.randint(1000000, 9999999)}"
        total_amount = float(quantity * valor_unitario)

        cur.execute("""
            INSERT INTO Adquiridos (
                order_id_interno, nome_cliente, email_cliente, cpf_cliente, telefone_cliente,
                quantidade, tokens_ids_db, tokens_numeros_db, status_compra, total_pago, data_criacao_pedido, data_ultima_atualizacao
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id;
        """,
        (
            order_id_interno, nome, email, cpf, phone, quantity,
            ','.join(assigned_token_ids), ','.join(assigned_token_numeros),
            'pending', total_amount
        ))
        adquiridos_id = cur.fetchone()['id']
        logging.info(f"Pedido pendente ID {adquiridos_id} (Order: {order_id_interno}) inserido no banco com {quantity} tokens: {', '.join(assigned_token_numeros)}")
        conn.commit()

    except psycopg2.Error as db_err:
        if conn:
            conn.rollback()
        logging.error(f"❌ Erro de Banco de Dados em /create_preference: {db_err}")
        return jsonify({'success': False, 'message': 'Erro ao processar seu pedido. Tente novamente mais tarde.'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"❌ Erro Geral em /create_preference: {e}")
        return jsonify({'success': False, 'message': 'Ocorreu um erro inesperado. Tente novamente.'}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.autocommit = True
            conn.close()

    item = {
        "title": f"Números da Sorte ({quantity} un.) - Pedido {order_id_interno}",
        "quantity": 1,
        "unit_price": total_amount,
        "currency_id": "BRL"
    }
    payer = {
        "name": nome, "email": email,
        "identification": {"type": "CPF", "number": cpf},
        "phone": {"area_code": phone[:2] if len(phone) >= 10 else "", "number": phone[2:] if len(phone) >= 10 else phone}
    }
    # Definição robusta do base_url para produção Vercel
    base_url = os.getenv('VERCEL_URL', 'http://127.0.0.1:5000')
    if base_url and not base_url.startswith('http'):
        base_url = f'https://{base_url}'
    if base_url.startswith('http://127.0.0.1'):
        logging.warning("Usando URL base local (http://127.0.0.1:5000). Webhook do Mercado Pago e retornos automáticos podem não funcionar corretamente sem um túnel HTTPS público (ex: ngrok) ou deploy.")
    else:
        logging.info(f"Usando base_url: {base_url} para URLs do Mercado Pago.")

    preference_data = {
        "items": [item],
        "payer": payer,
        "external_reference": order_id_interno,
        "notification_url": f"{base_url}/mercadopago_webhook",
        "auto_return": "all",
        "back_urls": {
            "success": f"{base_url}/payment_status?status=success&order_id={order_id_interno}",
            "pending": f"{base_url}/payment_status?status=pending&order_id={order_id_interno}",
            "failure": f"{base_url}/payment_status?status=failure&order_id={order_id_interno}"
        }
    }

    try:
        sdk = get_mp_sdk()
        if not sdk:
            return jsonify({'success': False, 'message': 'Erro na configuração do sistema de pagamento.'}), 500
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        payment_link = preference["init_point"]
        logging.info(f"Preferência MP criada para Order ID {order_id_interno}. Link: {payment_link}")
        return jsonify({'success': True, 'payment_link': payment_link, 'preference_id': preference['id']})

    except Exception as e_mp:
        logging.error(f"❌ Erro ao criar preferência no Mercado Pago para {order_id_interno}: {e_mp}")
        return jsonify({'success': False, 'message': f'Erro ao iniciar pagamento com Mercado Pago. Tente mais tarde.'}), 500

# Endpoint para receber notificações do Mercado Pago (IPN - Instant Payment Notification)
# ESTA É A PARTE CRÍTICA PARA CONFIRMAR O PAGAMENTO!
@app.route('/mercadopago_webhook', methods=['GET', 'POST'])
def mercadopago_webhook():
    logging.info("🔔 Notificação de Mercado Pago Webhook recebida!")
    if request.method == 'GET':
        logging.info(f"Webhook GET request: {request.args}")
        return "OK", 200
    elif request.method == 'POST':
        notification_data = request.args
        topic = notification_data.get('topic')
        resource_id = notification_data.get('id')
        logging.info(f"Webhook POST request: Topic='{topic}', Resource ID='{resource_id}'")
        if topic == 'payment':
            sdk = get_mp_sdk()
            if not sdk:
                logging.error('❌ SDK Mercado Pago não configurado.')
                return "OK", 200
            try:
                payment_info = sdk.payment().get(resource_id)
                payment_status = payment_info["response"].get("status")
                external_reference = payment_info["response"].get("external_reference")
                payment_id_mp = payment_info["response"].get("id")
                logging.info(f"Notificação de Pagamento - ID: {resource_id}, Status: {payment_status}, External Ref: {external_reference}")
                conn = get_db_connection()
                cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cur.execute("SELECT * FROM Adquiridos WHERE order_id_interno = %s FOR UPDATE;", (external_reference,))
                compra = cur.fetchone()
                if not compra:
                    logging.warning(f"⚠️ Pedido não encontrado para external_reference '{external_reference}' no banco.")
                    cur.close()
                    conn.close()
                    return "OK", 200
                if payment_status == 'approved':
                    if compra['status_compra'] != 'approved':
                        logging.info(f"✅ Pagamento APROVADO para Order ID: {external_reference}. Processando compra.")
                        # Atualiza status e payment_id_mp
                        cur.execute("""
                            UPDATE Adquiridos SET status_compra = 'approved', payment_id_mp = %s, data_ultima_atualizacao = CURRENT_TIMESTAMP
                            WHERE order_id_interno = %s;
                        """, (str(payment_id_mp), external_reference))
                        # Marca tokens como usados
                        token_ids = compra['tokens_ids_db'].split(',')
                        cur.execute(f"UPDATE Tokens SET disponivel = FALSE WHERE id IN ({','.join(['%s']*len(token_ids))});", token_ids)
                        conn.commit()
                        # Envia e-mails e Discord
                        try:
                            msg_customer = Message(
                                "Detalhes da sua Compra Confirmada - Sorteio do Carro",
                                recipients=[compra['email_cliente']],
                                body=f"""
Prezado(a) {compra['nome_cliente']},\n\nSeu pagamento foi CONFIRMADO com sucesso!\nObrigado por participar do nosso sorteio!\n\nAqui estão os detalhes da sua compra:\nNome: {compra['nome_cliente']}\nEmail: {compra['email_cliente']}\nCPF: {compra['cpf_cliente']}\nTelefone: {compra['telefone_cliente']}\nQuantidade de números da sorte: {compra['quantidade']}\nSeus números da sorte: {compra['tokens_numeros_db']}\n\nBoa sorte!\n"
                            )
                            mail.send(msg_customer)
                            msg_admin = Message(
                                f"✅ Compra Confirmada - Sorteio do Carro - {compra['nome_cliente']}",
                                recipients=[app.config['MAIL_DEFAULT_SENDER']],
                                body=f"""
COMPRA CONFIRMADA!\n\nCliente: {compra['nome_cliente']}\nEmail do Cliente: {compra['email_cliente']}\nCPF: {compra['cpf_cliente']}\nTelefone: {compra['telefone_cliente']}\nQuantidade de números comprados: {compra['quantidade']}\nTokens Atribuídos: {compra['tokens_numeros_db']}\nStatus do Pagamento (MP): APROVADO\nID do Pagamento (MP): {payment_id_mp}\n"
                            )
                            mail.send(msg_admin)
                            discord_message = (
                                f"🎉 COMPRA CONFIRMADA! 🎉\nCliente: **{compra['nome_cliente']}** ({compra['email_cliente']})\nComprou: **{compra['quantidade']}** números\nTotal: **R${compra['total_pago']:.2f}**\nTokens: `{compra['tokens_numeros_db']}`\nStatus MP: APROVADO\nID Pagamento MP: `{payment_id_mp}`"
                            )
                            send_discord_notification(discord_message, color=3066993)
                        except Exception as e:
                            logging.error(f"❌ Erro ao enviar e-mails/Discord de confirmação de compra APROVADA: {e}")
                    else:
                        logging.info(f"ℹ️ Pagamento APROVADO para Order ID: {external_reference}, mas já processado anteriormente.")
                elif payment_status == 'rejected':
                    if compra['status_compra'] != 'rejected':
                        logging.warning(f"❌ Pagamento REJEITADO para Order ID: {external_reference}.")
                        cur.execute("""
                            UPDATE Adquiridos SET status_compra = 'rejected', payment_id_mp = %s, data_ultima_atualizacao = CURRENT_TIMESTAMP
                            WHERE order_id_interno = %s;
                        """, (str(payment_id_mp), external_reference))
                        conn.commit()
                        discord_message = (
                            f"💔 PAGAMENTO REJEITADO! 💔\nCliente: **{compra['nome_cliente']}** ({compra['email_cliente']})\nTentou comprar: **{compra['quantidade']}** números\nTotal: **R${compra['total_pago']:.2f}**\nStatus MP: REJEITADO\nID Pagamento MP: `{payment_id_mp}`"
                        )
                        send_discord_notification(discord_message, color=15158332)
                    else:
                        logging.info(f"ℹ️ Pagamento REJEITADO para Order ID: {external_reference}, mas já processado anteriormente.")
                elif payment_status == 'pending':
                    if compra['status_compra'] != 'pending':
                        cur.execute("""
                            UPDATE Adquiridos SET status_compra = 'pending', payment_id_mp = %s, data_ultima_atualizacao = CURRENT_TIMESTAMP
                            WHERE order_id_interno = %s;
                        """, (str(payment_id_mp), external_reference))
                        conn.commit()
                        logging.info(f"⏳ Pagamento PENDENTE para Order ID: {external_reference}. Status atualizado.")
                cur.close()
                conn.close()
            except Exception as e:
                logging.error(f"❌ Erro ao processar webhook Mercado Pago: {e}")
                if 'cur' in locals():
                    cur.close()
                if 'conn' in locals():
                    conn.close()
        return "OK", 200
    return "Method Not Allowed", 405

@app.route('/payment_status')
def payment_status():
    status = request.args.get('status')
    order_id = request.args.get('order_id')
    logging.info(f"🌐 Cliente retornou da página de pagamento. Status: {status}, Order ID: {order_id}")
    if order_id:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM Adquiridos WHERE order_id_interno = %s;", (order_id,))
        compra = cur.fetchone()
        cur.close()
        conn.close()
        if compra:
            if compra['status_compra'] == 'approved':
                tokens = compra['tokens_numeros_db'].split(',') if compra['tokens_numeros_db'] else []
                return render_template('success.html', tokens=tokens)
            elif compra['status_compra'] == 'pending':
                return render_template('payment_pending.html')
            elif compra['status_compra'] == 'rejected':
                return render_template('payment_rejected.html')
    logging.warning(f"Retorno de pagamento para Order ID '{order_id}' não encontrado ou inválido.")
    return render_template('payment_generic_status.html', status=status)

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
    app.run(host="0.0.0.0", port=port)

# (Railway não é referenciado no app.py, mas pode haver arquivos railway.json ou variáveis relacionadas)
# Nenhuma referência Railway encontrada neste arquivo.