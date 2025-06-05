document.addEventListener('DOMContentLoaded', function() {
    // SEU CÓDIGO EXISTENTE PARA O MODAL DE COMPRA E FORMULÁRIO
    const comprarBtn = document.getElementById('comprarBtn');
    const modal = document.getElementById('modal');
    const closeBtn = document.querySelector('.close'); // Para o modal de compra
    const decreaseBtn = document.getElementById('decreaseQuantity');
    const increaseBtn = document.getElementById('increaseQuantity');
    const quantitySpan = document.getElementById('quantity');
    const valorTotalSpan = document.getElementById('valorTotal');
    const confirmarDadosBtn = document.getElementById('confirmarDados');
    const formMessage = document.getElementById('formMessage');

    let quantidade = 1;
    const valorUnitario = 10.00;

    function atualizarValor() {
        if (valorTotalSpan && quantitySpan) { // Verifica se os elementos existem
            valorTotalSpan.textContent = `R$${(quantidade * valorUnitario).toFixed(2)}`;
            quantitySpan.textContent = quantidade;
        }
    }

    function showMessage(message, isError = false) {
        if (formMessage) { // Verifica se o elemento existe
            formMessage.textContent = message;
            formMessage.classList.remove('hidden');
            if (isError) {
                formMessage.classList.add('error');
                formMessage.style.backgroundColor = ''; // Limpa a cor de sucesso se for erro
            } else {
                formMessage.classList.remove('error');
                formMessage.style.backgroundColor = '#2ecc71';
            }
        }
    }

    if (comprarBtn) {
        comprarBtn.addEventListener('click', function() {
            if (modal) {
                modal.style.display = 'flex';
            }
            if (formMessage) {
                formMessage.classList.add('hidden');
                formMessage.textContent = '';
            }
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            if (modal) {
                modal.style.display = 'none';
            }
        });
    }

    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            if (modal) {
                modal.style.display = 'none';
            }
        }
    });

    if (decreaseBtn) {
        decreaseBtn.addEventListener('click', function() {
            if (quantidade > 1) {
                quantidade--;
                atualizarValor();
            }
        });
    }

    if (increaseBtn) {
        increaseBtn.addEventListener('click', function() {
            if (quantidade < 2500) {
                quantidade++;
                atualizarValor();
            }
        });
    }
    
    if (quantitySpan) {
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
    }

    if (confirmarDadosBtn) {
        confirmarDadosBtn.addEventListener('click', function() {
            console.log('=== BOTÃO CONFIRMAR CLICADO ===');
            
            const nomeInput = document.getElementById('nome');
            const emailInput = document.getElementById('email');
            const cpfInput = document.getElementById('cpf');
            const telefoneInput = document.getElementById('telefone');

            console.log('Inputs encontrados:', {
                nome: nomeInput ? 'sim' : 'não',
                email: emailInput ? 'sim' : 'não',
                cpf: cpfInput ? 'sim' : 'não',
                telefone: telefoneInput ? 'sim' : 'não'
            });

            // Verifica se os inputs existem antes de pegar o .value
            const nome = nomeInput ? nomeInput.value.trim() : '';
            const email = emailInput ? emailInput.value.trim() : '';
            const cpf = cpfInput ? cpfInput.value.trim() : '';
            const telefone = telefoneInput ? telefoneInput.value.trim() : '';

            console.log('=== VALORES DOS CAMPOS ===');
            console.log('Nome:', nome);
            console.log('Email:', email);
            console.log('CPF:', cpf);
            console.log('Telefone:', telefone);

            if (!nome || !email || !cpf || !telefone) {
                showMessage('Por favor, preencha todos os campos do formulário.', true);
                return;
            }
            if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
                showMessage('Por favor, insira um endereço de e-mail válido.', true);
                return;
            }
            if (!/^\d{11}$/.test(cpf)) {
                showMessage('Por favor, insira um CPF válido (apenas números, 11 dígitos).', true);
                return;
            }
            if (!/^\d{10,11}$/.test(telefone)) {
                showMessage('Por favor, insira um telefone válido (apenas números, 10 ou 11 dígitos).', true);
                return;
            }

            // Salva os dados no localStorage após validação e antes de qualquer chamada
            try {
                console.log('=== INICIANDO SALVAMENTO NO LOCALSTORAGE ===');
                
                // Limpa dados antigos
                localStorage.clear(); // Limpa todo o localStorage para garantir
                console.log('localStorage limpo');

                // Salva novos dados
                localStorage.setItem('clientName', nome);
                localStorage.setItem('clientEmail', email);
                localStorage.setItem('clientCPF', cpf);
                localStorage.setItem('clientPhone', telefone);
                console.log('Dados salvos no localStorage');

                // Verifica se salvou
                const savedName = localStorage.getItem('clientName');
                const savedEmail = localStorage.getItem('clientEmail');
                const savedCPF = localStorage.getItem('clientCPF');
                const savedPhone = localStorage.getItem('clientPhone');

                console.log('=== VERIFICAÇÃO DOS DADOS SALVOS ===');
                console.log('Nome salvo:', savedName);
                console.log('Email salvo:', savedEmail);
                console.log('CPF salvo:', savedCPF);
                console.log('Telefone salvo:', savedPhone);

                if (!savedName || !savedEmail || !savedCPF || !savedPhone) {
                    throw new Error('Falha ao salvar dados no localStorage');
                }

                console.log('=== DADOS SALVOS COM SUCESSO ===');
            } catch (error) {
                console.error('Erro ao salvar dados:', error);
                showMessage('Erro ao salvar seus dados. Por favor, tente novamente.', true);
                return;
            }

            showMessage('Gerando o pagamento seguro...', false);

            // Salva os dados novamente antes do fetch
            try {
                localStorage.setItem('clientName', nome);
                localStorage.setItem('clientEmail', email);
                localStorage.setItem('clientCPF', cpf);
                localStorage.setItem('clientPhone', telefone);
                console.log('Dados salvos novamente antes do fetch');
            } catch (error) {
                console.error('Erro ao salvar dados antes do fetch:', error);
            }

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
                    
                    // Salva os dados novamente antes do redirecionamento
                    try {
                        console.log('=== SALVANDO DADOS ANTES DO REDIRECIONAMENTO ===');
                        localStorage.setItem('clientName', nome);
                        localStorage.setItem('clientEmail', email);
                        localStorage.setItem('clientCPF', cpf);
                        localStorage.setItem('clientPhone', telefone);
                        
                        // Verifica se salvou
                        const savedName = localStorage.getItem('clientName');
                        const savedEmail = localStorage.getItem('clientEmail');
                        const savedCPF = localStorage.getItem('clientCPF');
                        const savedPhone = localStorage.getItem('clientPhone');

                        console.log('=== VERIFICAÇÃO FINAL DOS DADOS ===');
                        console.log('Nome salvo:', savedName);
                        console.log('Email salvo:', savedEmail);
                        console.log('CPF salvo:', savedCPF);
                        console.log('Telefone salvo:', savedPhone);

                        if (!savedName || !savedEmail || !savedCPF || !savedPhone) {
                            throw new Error('Falha ao salvar dados antes do redirecionamento');
                        }
                        
                        console.log('Dados salvos com sucesso, redirecionando...');
                        window.location.href = data.payment_link;
                    } catch (error) {
                        console.error('Erro ao salvar dados antes do redirecionamento:', error);
                        // Continua com o redirecionamento mesmo se falhar
                        window.location.href = data.payment_link;
                    }
                } else {
                    showMessage(data.message || 'Ocorreu um erro ao gerar o pagamento.', true);
                }
            })
            .catch((error) => {
                console.error('Error:', error);
                showMessage('Ocorreu um erro na comunicação com o servidor para gerar o pagamento. Tente novamente.', true);
            });
        });
    }

    // Efeito typewriter
    const textoTypewriter = "Seu próximo carro pode estar a um PIX de distância!";
    const elTypewriter = document.querySelector('.typewriter-text');
    if (elTypewriter) {
        let i = 0;
        function type() {
            if (i < textoTypewriter.length) {
                elTypewriter.innerHTML = textoTypewriter.substring(0, i + 1) + '<span class="type-cursor">|</span>';
                i++;
                setTimeout(type, 45);
            } else {
                elTypewriter.textContent = textoTypewriter;
            }
        }
        type();
    }

    // --- INÍCIO: LÓGICA PARA O CARROSSEL DE IMAGENS ---
    const carouselTrack = document.querySelector('.carousel-track');
    const nextButtonCarousel = document.querySelector('.image-carousel-container .next');
    const prevButtonCarousel = document.querySelector('.image-carousel-container .prev');
    const indicatorsContainer = document.querySelector('.carousel-indicators');
    
    let carouselCards = [];
    let cardWidth = 0;
    let currentIndexCarousel = 0;
    let indicatorDots = [];

    if (carouselTrack) {
        carouselCards = Array.from(carouselTrack.children);

        function updateCardWidth() {
            if (carouselCards.length > 0) {
                cardWidth = carouselCards[0].getBoundingClientRect().width;
                // Se o carrossel estiver dentro de um container que pode estar oculto inicialmente,
                // a largura pode ser 0. Precisamos de uma estratégia para recalcular quando visível,
                // mas para este caso, vamos assumir que ele está visível ou a largura será definida corretamente no 'load'.
            }
        }

        if (indicatorsContainer && carouselCards.length > 0) {
            indicatorsContainer.innerHTML = ''; // Limpa indicadores existentes se houver
            carouselCards.forEach((_, index) => {
                const dot = document.createElement('button');
                dot.classList.add('indicator-dot');
                if (index === 0) {
                    dot.classList.add('active');
                }
                dot.setAttribute('aria-label', `Ir para imagem ${index + 1}`);
                dot.addEventListener('click', () => {
                    currentIndexCarousel = index;
                    updateCarousel();
                });
                indicatorsContainer.appendChild(dot);
            });
            indicatorDots = Array.from(indicatorsContainer.children);
        }

        function updateCarousel() {
            if (carouselTrack && cardWidth > 0) { // Só atualiza se cardWidth for válido
                 carouselTrack.style.transform = 'translateX(-' + (cardWidth * currentIndexCarousel) + 'px)';
            }
            if (indicatorDots.length > 0) {
                indicatorDots.forEach(dot => dot.classList.remove('active'));
                if (indicatorDots[currentIndexCarousel]) {
                     indicatorDots[currentIndexCarousel].classList.add('active');
                }
            }
        }

        if (nextButtonCarousel) {
            nextButtonCarousel.addEventListener('click', () => {
                currentIndexCarousel++;
                if (currentIndexCarousel >= carouselCards.length) {
                    currentIndexCarousel = 0; 
                }
                updateCarousel();
            });
        }

        if (prevButtonCarousel) {
            prevButtonCarousel.addEventListener('click', () => {
                currentIndexCarousel--;
                if (currentIndexCarousel < 0) {
                    currentIndexCarousel = carouselCards.length - 1; 
                }
                updateCarousel();
            });
        }
        
        // Atualizar a largura do card e o carrossel
        const initializeCarousel = () => {
            if (carouselCards.length > 0) {
                updateCardWidth();
                // Somente atualiza o carrossel se a largura do card for maior que 0
                if (cardWidth > 0) {
                    updateCarousel();
                } else {
                    // Se a largura do card ainda for 0, tenta novamente após um pequeno atraso
                    // Isso pode acontecer se o carrossel ou suas imagens não estiverem totalmente renderizados
                    // ou se as imagens não tiverem dimensões intrínsecas e o CSS não definir uma largura/altura.
                    setTimeout(initializeCarousel, 100);
                }
            }
        };
        
        // Tenta inicializar no DOMContentLoaded, mas a imagem pode não ter carregado.
        // A melhor abordagem seria após o carregamento da primeira imagem ou no window.load.
        window.addEventListener('load', initializeCarousel); // Garante que imagens e CSS foram processados
        window.addEventListener('resize', () => {
            // Timeout para garantir que o resize terminou antes de recalcular
            setTimeout(() => {
                updateCardWidth();
                if (cardWidth > 0) {
                    updateCarousel();
                }
            }, 100);
        });

    }
    // --- FIM: LÓGICA PARA O CARROSSEL DE IMAGENS ---


    // --- INÍCIO: LÓGICA PARA O MODAL DA FICHA TÉCNICA ---
    const fichaTecnicaModal = document.getElementById('fichaTecnicaModal');
    const btnAbrirFichaTecnica = document.getElementById('btnAbrirFichaTecnica');
    const closeFichaBtn = document.getElementById('closeFichaBtn');

    if (btnAbrirFichaTecnica) {
        btnAbrirFichaTecnica.addEventListener('click', function() {
            if (fichaTecnicaModal) {
                fichaTecnicaModal.style.display = 'flex'; // Ou 'flex' se você preferir esse display
            }
        });
    }

    if (closeFichaBtn) {
        closeFichaBtn.addEventListener('click', function() {
            if (fichaTecnicaModal) {
                fichaTecnicaModal.style.display = 'none';
            }
        });
    }

    window.addEventListener('click', function(event) {
        if (event.target === fichaTecnicaModal) {
            if (fichaTecnicaModal) {
                fichaTecnicaModal.style.display = 'none';
            }
        }
        // O listener para fechar o modal de compra (event.target === modal) já existe acima,
        // então não precisamos duplicá-lo aqui. Este listener agora cuida do modal da ficha técnica.
    });
    // --- FIM: LÓGICA PARA O MODAL DA FICHA TÉCNICA ---

    atualizarValor(); // Chamada inicial para o modal de compra
});