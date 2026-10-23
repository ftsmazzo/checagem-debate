# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

A pessoa que assiste o debate vem primeiro: quer ler a fala, o carimbo, o contexto, a fonte e gerar o card para compartilhar. Quem opera o painel é o segundo público. O painel, com senha, serve para ligar a escuta, publicar correção e tirar uma checagem do ar.

## Product Purpose

Checar fala de debate enquanto ela está no ar e deixar a checagem legível, com fonte. Sucesso é a pessoa que assiste encontrar o carimbo e a página que o sustenta durante o debate, e o arquivo do debate continuar recuperável depois. Um áudio processado só depois que o debate acaba não é o produto.

## Positioning

O Mentirômetro mostra o estado da fala e a fonte. Não dá nota de quem ganhou, não usa a palavra fake como carimbo e não reduz o debate a uma porcentagem de mentira. Carimbo fechado só permanece com URL https. Uma segunda leitura, sem o nome de quem falou, impede carimbo fechado quando discorda de verdade. Promessa é categoria própria, não é erro. O sistema não busca, não grava e não retransmite o sinal da emissora. Quem opera cola o link ao vivo que já tem.

## Operating Context

Debate Lula × Flávio na TV Globo, 23/10/2026, às 21h20. Essa transmissão não passa na rádio. O debate da Band em 18/10 permanece no banco e também aparece na leitura pública, junto com as checagens novas. A escuta de hoje aceita URL de YouTube, o preset da BandNews e endereços da lista já existente (domínios do YouTube, streamtheworld e links .m3u8). Outros canais entram depois, no mesmo encaixe. `/health` é público. A leitura em `/leitura` e o método em `/metodo` são públicos. O restante do painel exige senha.

## Capabilities and Constraints

A fila automática checa fala atribuída a Lula e a Flávio. Checagem manual pode ser avulsa, sem debate. A transcrição gravada não se apaga ao limpar a fila, e o que já foi resolvido também permanece. Zerar não apaga trechos. O arquivo da Band não é reprocessado por uma troca de régua.

Carimbos fechados: sustentado, sustentado com ressalva, não é bem assim, exagerado, distorcido, contradito, sem prova. Em aberto: sem prova pública, versões em disputa, indício, dados incompletos, áudio confuso. Os estados antigos sem evidência e inconclusivo continuam válidos no arquivo. Cada fonte guarda tipo (oficial, checagem, imprensa) e um trecho curto. A leitura pública filtra por candidato, carimbo e tema. O botão "Achei um erro" envia um aviso; quem publica a correção no card é o painel.

Fora deste produto: Pix, anúncio, contador de visitas, quiz, Instagram, TikTok, app instalável e aviso no celular. Repositório privado. Transcrição bruta e vereditos não são matéria sem revisão humana. Banco exclusivo deste projeto.

Em aberto: adaptar a escuta a canais além da lista atual.

## Brand Commitments

O nome do sistema é Mentirômetro. A marca ao lado é IEleitoral, com o logo em `app/static/logo-ie.png`. A voz nomeia o estado e a fonte. Não rotula a frase como fake. O visual do Fato Carimbado não é modelo para copiar. O visual atual do painel não é a identidade a estender.

## Evidence on Hand

Há transcrição e checagens reais do debate Band — 18/10 no banco deste projeto. O card de imagem (feed e Stories) já é gerado no navegador a partir da checagem. Não há depoimento, audiência medida nem peça de imprensa para citar. Trabalho futuro não inventa esses materiais.

## Product Principles

- A checagem sai enquanto a fala está no ar.
- Sem URL https não há carimbo fechado.
- O painel mostra o estado e a fonte, nunca um rótulo de fake.
- Promessa não é erro, e não há ranking de vencedor.
- O arquivo de um debate permanece quando o próximo começa.
