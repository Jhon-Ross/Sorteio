document.addEventListener('DOMContentLoaded', function() {
    const comprarBtn = document.getElementById('comprarBtn');
    const modal = document.getElementById('modal');
    const closeBtn = document.querySelector('.close');
    const decreaseBtn = document.getElementById('decreaseQuantity');
    const increaseBtn = document.getElementById('increaseQuantity');
    const quantitySpan = document.getElementById('quantity');
    const valorTotalSpan = document.getElementById('valorTotal');
    const confirmarDadosBtn = document.getElementById('confirmarDados');
    const formMessage = document.getElementById('formMessage'); // Elemento para mensagens de feedback

    let quantidade = 1;
    const valorUnitario = 10.00;

    function atualizarValor() {
        valorTotalSpan.textContent = `R$${(quantidade * valorUnitario).toFixed(2)}`;
        quantitySpan.textContent = quantidade;
    }

    // Função para exibir mensagens amigáveis
    function showMessage(message, isError = false) {
        formMessage.textContent = message;
        formMessage.classList.remove('hidden');
        if (isError) {
            formMessage.classList.add('error');
        } else {
            formMessage.classList.remove('error');
            formMessage.style.backgroundColor = '#2ecc71'; // Cor verde para sucesso
        }
    }

    comprarBtn.addEventListener('click', function() {
        modal.style.display = 'flex';
        // Limpa mensagens anteriores ao abrir o modal
        formMessage.classList.add('hidden');
        formMessage.textContent = '';
    });

    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    // Fecha o modal ao clicar fora do conteúdo
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    decreaseBtn.addEventListener('click', function() {
        if (quantidade > 1) {
            quantidade--;
            atualizarValor();
        }
    });

    increaseBtn.addEventListener('click', function() {
        if (quantidade < 2500) {
            quantidade++;
            atualizarValor();
        }
    });

    // Torna a quantidade editável ao clicar
    quantitySpan.contentEditable = true;
    quantitySpan.style.cursor = 'pointer';
    quantitySpan.title = 'Clique para editar';

    quantitySpan.addEventListener('blur', function() {
        let valor = parseInt(quantitySpan.textContent.replace(/\D/g, ''));
        if (isNaN(valor) || valor < 1) valor = 1;
        if (valor > 2500) valor = 2500;
        quantidade = valor;
        atualizarValor();
    });

    quantitySpan.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            quantitySpan.blur();
        }
    });

    confirmarDadosBtn.addEventListener('click', function() {
        const nome = document.getElementById('nome').value.trim();
        const email = document.getElementById('email').value.trim();
        const cpf = document.getElementById('cpf').value.trim();
        const telefone = document.getElementById('telefone').value.trim();

        // Validação dos campos
        if (!nome || !email || !cpf || !telefone) {
            showMessage('Por favor, preencha todos os campos do formulário.', true);
            return;
        }

        // Validação de email básica
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            showMessage('Por favor, insira um endereço de e-mail válido.', true);
            return;
        }

        // Validação de CPF (apenas verifica se tem 11 dígitos, pode ser mais robusta)
        if (!/^\d{11}$/.test(cpf)) {
            showMessage('Por favor, insira um CPF válido (apenas números, 11 dígitos).', true);
            return;
        }

        // Validação de telefone (apenas verifica se tem no mínimo 10 dígitos, pode ser mais robusta)
        if (!/^\d{10,11}$/.test(telefone)) {
            showMessage('Por favor, insira um telefone válido (apenas números, 10 ou 11 dígitos).', true);
            return;
        }

        showMessage('Gerando o pagamento seguro...', false); // Mensagem de processamento

        // Envia dados para o backend Flask para criar a preferência de pagamento
        fetch('/create_preference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: nome,
                email: email,
                cpf: cpf,
                phone: telefone,
                quantity: quantidade
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage('Redirecionando para o Mercado Pago...', false);
                // Redireciona o usuário para o link de pagamento do Mercado Pago
                window.location.href = data.payment_link;
            } else {
                showMessage(data.message || 'Ocorreu um erro ao gerar o pagamento.', true);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            showMessage('Ocorreu um erro na comunicação com o servidor para gerar o pagamento. Tente novamente.', true);
        });
    });

    atualizarValor();
});