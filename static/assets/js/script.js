document.addEventListener('DOMContentLoaded', function () {
    const comprarBtn = document.getElementById('comprarBtn');
    const modal = document.getElementById('modal');
    const closeBtn = document.querySelector('.close');
    const decreaseQuantityBtn = document.getElementById('decreaseQuantity');
    const increaseQuantityBtn = document.getElementById('increaseQuantity');
    const quantitySpan = document.getElementById('quantity');
    const confirmarDadosBtn = document.getElementById('confirmarDados');
    const formSection = document.getElementById('formSection');
    const formMessage = document.getElementById('formMessage');
    const valorTotalSpan = document.getElementById('valorTotal');

    let quantity = 1;
    const ticketPrice = 10.00;

    comprarBtn.addEventListener('click', function () {
        modal.style.display = 'flex';
    });

    closeBtn.addEventListener('click', function () {
        modal.style.display = 'none';
    });

    decreaseQuantityBtn.addEventListener('click', function () {
        if (quantity > 1) {
            quantity--;
            quantitySpan.textContent = quantity;
            valorTotalSpan.textContent = `R$${(quantity * ticketPrice).toFixed(2)}`;
        }
    });

    increaseQuantityBtn.addEventListener('click', function () {
        quantity++;
        quantitySpan.textContent = quantity;
        valorTotalSpan.textContent = `R$${(quantity * ticketPrice).toFixed(2)}`;
    });

    function showMessage(message, isError = false) {
        formMessage.textContent = message;
        formMessage.classList.remove('hidden');
        formMessage.classList.toggle('error', isError);
    }

    function hideMessage() {
        formMessage.classList.add('hidden');
    }

    confirmarDadosBtn.addEventListener('click', function () {
        const nome = document.getElementById('nome').value;
        const email = document.getElementById('email').value;
        const cpf = document.getElementById('cpf').value;
        const telefone = document.getElementById('telefone').value;

        hideMessage();

        // Validar os dados do formulário
        if (!nome || !email || !cpf || !telefone) {
            showMessage('Por favor, preencha todos os campos.', true);
            return;
        }

        // Validar o formato do nome (apenas letras e espaços)
        const nomeRegex = /^[A-Za-z\s]+$/;
        if (!nomeRegex.test(nome)) {
            showMessage('Por favor, insira um nome válido (apenas letras e espaços).', true);
            return;
        }

        // Validar o formato do e-mail
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            showMessage('Por favor, insira um e-mail válido.', true);
            return;
        }

        // Validar o formato do CPF (11 dígitos)
        const cpfRegex = /^\d{11}$/;
        if (!cpfRegex.test(cpf)) {
            showMessage('Por favor, insira um CPF válido (11 dígitos).', true);
            return;
        }

        // Validar o formato do telefone (DD + 9 dígitos)
        const telefoneRegex = /^\d{11}$/;
        if (!telefoneRegex.test(telefone)) {
            showMessage('Por favor, insira um telefone válido (DD + 9 dígitos).', true);
            return;
        }

        // Enviar os dados para o servidor
        fetch('/enviar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                nome: nome,
                email: email,
                cpf: cpf,
                telefone: telefone
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === "E-mail enviado com sucesso") {
                    showMessage('Dados enviados para o e-mail com sucesso!');
                } else {
                    showMessage('Erro ao enviar os dados para o e-mail: ' + data.message, true);
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                showMessage('Erro ao enviar os dados para o e-mail.', true);
            });

        // Se os dados forem válidos, enviar para o servidor
        fetch('/checkout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                nome: nome,
                email: email,
                cpf: cpf,
                telefone: telefone,
                quantity: quantity
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.init_point) {
                    window.location.href = data.init_point;
                } else {
                    showMessage('Erro ao redirecionar para o Mercado Pago: ' + data.message, true);
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                showMessage('Erro ao redirecionar para o Mercado Pago.', true);
            });
    });
});
