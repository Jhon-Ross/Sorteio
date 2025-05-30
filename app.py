from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os
from flask_sqlalchemy import SQLAlchemy
import csv
import mysql.connector  # Importe o conector MySQL
import mercadopago
import json
import requests
import logging

# Carrega variáveis do .env
load_dotenv()

app = Flask(__name__)

# Configurações de e-mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mail = Mail(app)

# Configurações do Banco de Dados
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configurações do Mercado Pago
sdk = mercadopago.SDK(os.getenv("MERCADO_PAGO_ACCESS_TOKEN"))
MERCADO_PAGO_PUBLIC_KEY = os.getenv("MERCADO_PAGO_PUBLIC_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Modelos do Banco de Dados


class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(4), unique=True, nullable=False)
    disponivel = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Token {self.token}>'


class Compra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(4), db.ForeignKey(
        'token.token'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<Compra {self.id}>'

# Função para ler os tokens do arquivo CSV e adicionar ao banco de dados


def popular_tokens():
    with open("tokens.csv", "r") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Pular o cabeçalho
        for row in reader:
            token = row[0]
            # Verificar se o token já existe no banco de dados
            existing_token = Token.query.filter_by(token=token).first()
            if not existing_token:
                novo_token = Token(token=token)
                db.session.add(novo_token)
    db.session.commit()

# Função para obter um token aleatório disponível


def obter_token_disponivel(quantidade):
    tokens = Token.query.filter_by(disponivel=True).limit(quantidade).all()
    if len(tokens) == quantidade:
        token_values = [token.token for token in tokens]
        for token in tokens:
            token.disponivel = False
        db.session.commit()
        return token_values
    else:
        return None

# ✅ Rota para carregar a página HTML


@app.route('/')
def index():
    return render_template('index.html', mercado_pago_public_key=MERCADO_PAGO_PUBLIC_KEY)


@app.route('/enviar', methods=['POST'])
def enviar_email():
    try:
        data = request.get_json()
        logging.debug(f"Dados recebidos em /enviar: {data}")
        msg = Message(
            subject='Novo cadastro no sorteio',
            sender=app.config['MAIL_USERNAME'],
            recipients=[os.getenv('DESTINATARIO_PADRAO',
                                  app.config['MAIL_USERNAME'])],
            body=f"""Nome: {data.get('nome')}
Email: {data.get('email')}
CPF: {data.get('cpf')}
Telefone: {data.get('telefone')}"""
        )
        mail.send(msg)
        return jsonify({"status": "E-mail enviado com sucesso"}), 200
    except Exception as e:
        logging.exception("Erro ao processar /enviar")
        return jsonify({"status": "Erro", "message": str(e)}), 500


@app.route('/checkout', methods=['POST'])
def checkout():
    try:
        data = request.get_json()
        logging.debug(f"Dados recebidos em /checkout: {data}")
        nome = data.get('nome')
        email = data.get('email')
        cpf = data.get('cpf')
        telefone = data.get('telefone')
        quantity = data.get('quantity')

        # Enviar e-mail
        msg = Message(
            subject='Novo cadastro no sorteio',
            sender=app.config['MAIL_USERNAME'],
            recipients=[os.getenv('DESTINATARIO_PADRAO',
                                  app.config['MAIL_USERNAME'])],
            body=f"""Nome: {nome}
Email: {email}
CPF: {cpf}
Telefone: {telefone}"""
        )
        mail.send(msg)

        # Cria um item na preferência
        item = {
            "title": "Sorteio",
            "quantity": quantity,
            "unit_price": 10.00  # Valor fixo de R$10,00
        }

        # Dados do comprador
        payer = {
            "name": nome,
            "email": email,
            "identification": {
                "type": "CPF",
                "number": cpf
            }
        }

        # Cria a preferência
        preference_data = {
            "items": [item],
            "payer": payer,
            "payment_methods": {
                "excluded_payment_types": [
                    {
                        "id": "credit_card"
                    },
                    {
                        "id": "debit_card"
                    }
                ]
            },
            "back_urls": {
                # URL de sucesso
                "success": request.url_root + "success?status=success&nome=" + nome + "&email=" + email + "&cpf=" + cpf + "&telefone=" + telefone + "&quantity=" + str(quantity),
                "failure": request.url_root + "feedback?status=failure",  # URL de falha
                "pending": request.url_root + "feedback?status=pending"   # URL de pendente
            },
            "auto_return": "approved",
            "notification_url": request.url_root + "webhook"  # URL para receber notificações
        }

        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]

        return jsonify({
            "init_point": preference.get('init_point')
        })

    except Exception as e:
        logging.exception("Erro ao processar /checkout")
        return jsonify({"message": str(e)}), 500


@app.route('/feedback')
def feedback():
    status = request.args.get('status')
    nome = request.args.get('nome')
    email = request.args.get('email')
    cpf = request.args.get('cpf')
    telefone = request.args.get('telefone')
    quantity = int(request.args.get('quantity'))

    if status == 'success':
        # Obter tokens disponíveis do banco de dados
        tokens = obter_token_disponivel(quantity)

        if tokens:
            # Criar registros de compra no banco de dados
            for token in tokens:
                compra = Compra(token=token, nome=nome, email=email,
                                cpf=cpf, telefone=telefone)
                db.session.add(compra)
            db.session.commit()

            # Enviar os tokens por e-mail
            msg = Message(
                subject='Seus números da sorte!',
                sender=app.config['MAIL_USERNAME'],
                recipients=[email],
                body=f"Seus números da sorte são: {', '.join(tokens)}"
            )
            mail.send(msg)

            # Enviar os tokens por WhatsApp (simulação)
            print(f"Enviando tokens {tokens} para o WhatsApp {telefone}")

            # Renderizar o template de sucesso com os tokens
            return render_template('success.html', tokens=tokens)
        else:
            return "<h1>Todos os tokens já foram utilizados!</h1>"
    elif status == 'failure':
        return render_template('failure.html')  # Crie um template failure.html
    else:
        return render_template('pending.html')  # Crie um template pending.html


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        request_info = request.get_json()
        payment_id = request_info.get('data', {}).get('id')
        topic = request_info.get('topic')

        if topic == 'payment':
            payment_response = sdk.payment().get(payment_id)
            payment_info = payment_response["response"]
            payment_status = payment_info["status"]
            external_reference = payment_info.get("external_reference", "N/A")
            payer_email = payment_info["payer"]["email"]

            # Enviar notificação para o Discord
            discord_data = {
                "content": f"Novo pagamento recebido!\nID: {payment_id}\nStatus: {payment_status}\nEmail do pagador: {payer_email}\nReferência Externa: {external_reference}"
            }
            requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(
                discord_data), headers={"Content-Type": "application/json"})

            print(
                f"Webhook recebido. Payment ID: {payment_id}, Status: {payment_status}")
            return jsonify({"status": "OK"}), 200
        else:
            print(f"Tópico não suportado recebido: {topic}")
            return jsonify({"status": "OK"}), 200
    except Exception as e:
        print(f"Erro ao processar webhook: {str(e)}")
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route('/success')
def success():
    nome = request.args.get('nome')
    email = request.args.get('email')
    cpf = request.args.get('cpf')
    telefone = request.args.get('telefone')
    quantity = int(request.args.get('quantity'))

    # Obter tokens disponíveis do banco de dados
    tokens = obter_token_disponivel(quantity)

    if tokens:
        # Criar registros de compra no banco de dados
        for token in tokens:
            compra = Compra(token=token, nome=nome, email=email,
                            cpf=cpf, telefone=telefone)
            db.session.add(compra)
        db.session.commit()

        # Enviar os tokens por e-mail
        msg = Message(
            subject='Seus números da sorte!',
            sender=app.config['MAIL_USERNAME'],
            recipients=[email],
            body=f"Seus números da sorte são: {', '.join(tokens)}"
        )
        mail.send(msg)

        # Enviar os tokens por WhatsApp (simulação)
        print(f"Enviando tokens {tokens} para o WhatsApp {telefone}")

        # Renderizar o template de sucesso com os tokens
        return render_template('success.html', tokens=tokens)
    else:
        return "<h1>Todos os tokens já foram utilizados!</h1>"


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Cria as tabelas no banco de dados
        popular_tokens()  # Adiciona os tokens do CSV ao banco
    app.run(debug=True)
