# Pacote — Mentirômetro no debate da Globo

Debate: Lula × Flávio, TV Globo, sexta 23/10/2026, 21h20.
A transmissão não passa na rádio. Checar um arquivo depois que o debate acabar não serve: a checagem tem de sair enquanto a fala está no ar. O Mentirômetro não busca, não grava e não retransmite o sinal da Globo. Na hora, quem opera cola o link ao vivo do canal que estiver transmitindo. Outros canais entram depois, no mesmo encaixe.

O visual novo fica para depois deste pacote. Aí entra `/impeccable init` e, em seguida, a troca da interface. Este arquivo não desenha tela.

## O que fica de fora

Não entra neste pacote: Pix, anúncio, contador de visitas, quiz, Instagram, TikTok, app instalável e aviso no celular. Também não entra nota de quem ganhou o debate.

## O que entra

1. Os dois candidatos na mesma régua. A fila deixa de checar só Lula.
2. Carimbos no lugar da porcentagem de mentira: sustentado, sustentado com ressalva, não é bem assim, exagerado, distorcido, contradito, sem prova. O que não fecha fica em aberto (sem prova pública, versões em disputa, indício, dados incompletos, áudio confuso). Promessa é categoria própria, não é erro.
3. Segunda leitura, sem o nome de quem falou. Se discordar de verdade, não sai carimbo fechado.
4. Cada fonte guarda o tipo (oficial, checagem, imprensa) e um trecho curto da página. Sem URL https, não há carimbo fechado.
5. Escuta ao vivo pelo link do canal. A transcrição deixa de ser um picadinho de poucos segundos: os trechos se juntam em falas, e a tela mostra essas falas, não cada pedaço de áudio.
6. Página pública, sem senha, só para ler: fala, carimbo, contexto, fontes e o card de imagem (feed e Stories). O painel com senha continua sendo o lugar de ligar a escuta, corrigir e tirar do ar.
7. Filtro por candidato, carimbo e tema. Tema sai da própria checagem (saúde, economia, segurança e os demais que aparecerem).
8. Botão "Achei um erro" na página pública. A correção aparece no card, com o motivo. Quem publica a correção é o painel.
9. Uma página curta de método, escrita antes do debate, com a régua acima.

O arquivo da Band em 18/10 permanece. Não é apagado e não é reprocessado neste pacote.

## Ordem

1. Motor: os dois candidatos, carimbos, segunda leitura, fontes com trecho, escuta ao vivo por link e transcrição em falas.
2. Página pública de leitura e o card de imagem em cima dos dados novos. Visual ainda o atual, só para funcionar na noite.
3. `/impeccable init` grava o que o produto é. Depois a interface inteira é trocada: painel, página pública e card. O visual de hoje serve só de referência do que não repetir.

A noite de sexta usa o passo 2 se o áudio chegar a tempo. O passo 3 não entra na transmissão.
