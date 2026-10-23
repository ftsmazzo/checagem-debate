---
name: Mentirômetro
description: A checagem do debate na noite da Inteligência Eleitoral.
colors:
  night: "#0c0c0c"
  paper: "#f6f3ee"
  coral: "#f15d5a"
  mark: "#4ab848"
  plate: "#161616"
  line: "#3a3532"
  bg-soft: "#121212"
  ink-soft: "#ddd6cc"
  muted: "#b7b0a6"
  coral-deep: "#ff8a86"
  coral-soft: "rgba(241, 93, 90, 0.16)"
  accent-soft: "rgba(74, 184, 72, 0.16)"
  success: "#3dce8f"
  ressalva: "#b7d36a"
  warn: "#e2b34a"
  exagerado: "#f0a05a"
  distorcido: "#f3a0a8"
  danger: "#ff6b6b"
  sem-prova: "#c8c2ba"
  aberto: "#a9bdd4"
typography:
  display:
    fontFamily: '"Archivo Black", sans-serif'
    fontSize: "clamp(1.8rem, 3.2vw, 2.7rem)"
    fontWeight: 400
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  headline:
    fontFamily: '"Archivo Black", sans-serif'
    fontSize: "clamp(1.6rem, 3vw, 2.2rem)"
    fontWeight: 400
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  title:
    fontFamily: '"Archivo Black", sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "0.04em"
  body:
    fontFamily: "Literata, Georgia, serif"
    fontSize: "1.05rem"
    lineHeight: 1.55
  label:
    fontFamily: '"Archivo Black", sans-serif'
    fontSize: "0.72rem"
    fontWeight: 400
    letterSpacing: "0.04em"
rounded:
  ie-radius: "0px"
  ie-radius-sm: "0px"
spacing:
  "8": "8px"
  "10": "10px"
  "12": "12px"
  "14": "14px"
  "16": "16px"
  "28": "28px"
  "40": "40px"
components:
  button-primary:
    backgroundColor: "{colors.coral}"
    textColor: "{colors.night}"
    rounded: "{rounded.ie-radius-sm}"
    padding: "10px 14px"
  button-primary-hover:
    backgroundColor: "{colors.coral-deep}"
    textColor: "{colors.night}"
    rounded: "{rounded.ie-radius-sm}"
    padding: "10px 14px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.ie-radius-sm}"
    padding: "10px 14px"
  button-ghost-hover:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.paper}"
    rounded: "{rounded.ie-radius-sm}"
    padding: "10px 14px"
  input:
    backgroundColor: "{colors.bg-soft}"
    textColor: "{colors.paper}"
    rounded: "{rounded.ie-radius-sm}"
    padding: "10px 12px"
  nav-link:
    backgroundColor: "transparent"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.ie-radius}"
    padding: "0 12px"
    height: "40px"
  nav-link-current:
    backgroundColor: "{colors.coral}"
    textColor: "{colors.night}"
    typography: "{typography.label}"
    rounded: "{rounded.ie-radius}"
    padding: "0 12px"
    height: "40px"
  nav-link-hover:
    backgroundColor: "transparent"
    textColor: "{colors.mark}"
    typography: "{typography.label}"
    rounded: "{rounded.ie-radius}"
    padding: "0 12px"
    height: "40px"
  plate:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.paper}"
    rounded: "{rounded.ie-radius}"
    padding: "16px"
  stamp:
    backgroundColor: "transparent"
    textColor: "{colors.paper}"
    rounded: "{rounded.ie-radius}"
    padding: "5px 10px"
  share-card:
    backgroundColor: "{colors.night}"
    textColor: "{colors.paper}"
    rounded: "{rounded.ie-radius}"
    padding: "88px"
    width: "1080px"
---

# Design System: Mentirômetro

## Overview

**Creative North Star: "A mesa do debate"**

A checagem acontece na noite da Inteligência Eleitoral. O fundo é o preto do logo, a placa sobe um degrau, o texto é papel quente. O coral do logo marca a seção atual, o botão principal e a moldura do card. O verde do monograma marca o foco e o que está entrando agora.

A densidade é de leitura. A fala citada entra em Archivo Black, o carimbo é contorno duplo levemente inclinado, os cantos são retos. O resumo e o texto corrido ficam em Literata. A profundidade vem do degrau entre noite, placa e campo. O quadro claro e o chip preenchido ficam de fora desta mesa.

**Key Characteristics:**

- Noite, placa e papel quente, com a linha morna entre os blocos
- Coral na seção atual, no botão principal e na moldura do card
- Verde no foco, no hover da navegação e em “entrando agora”
- Carimbo vazado, inclinado, na tinta do estado
- Archivo Black no nome, no carimbo e na fala citada; Literata no texto e no resumo
- Cantos retos e sombra nenhuma

## Colors

A paleta é a do logo: noite, coral e verde, com o papel quente por cima da placa.

### Primary

- **Coral do logo** (#f15d5a): seção atual da navegação, botão principal, seleção de texto, risco de 2px sob o cabeçalho, caret dos campos e os quatro lados do card. O texto sobre o preenchimento é a noite.

### Secondary

- **Verde do monograma** (#4ab848): anel de foco, hover do item de navegação, “entrando agora” e o aviso AO VIVO. Não preenche o botão principal.

### Neutral

- **Noite** (#0c0c0c): fundo da página, do cabeçalho e do card. `color-scheme: dark`.
- **Placa** (#161616): bloco de trabalho, formulário, login e trecho do placar.
- **Campo** (#121212): fundo de input, select e textarea.
- **Linha** (#3a3532): borda de 1px da placa, do campo e do item de navegação em repouso.
- **Papel** (#f6f3ee): texto principal e a fala no card.
- **Texto suave** (#ddd6cc): lead e texto secundário do ao vivo.
- **Meta** (#b7b0a6): metadado, placeholder e o que ainda não tem fonte na leitura.
- **Coral do hover** (#ff8a86): fundo do botão principal ao passar o mouse. É mais claro que o coral de repouso.
- **Coral lavado** (rgba(241, 93, 90, 0.16)): fundo do trecho marcado para checagem.
- **Verde lavado** (rgba(74, 184, 72, 0.16)): hover do botão fantasma no ao vivo.

As tintas de estado colorem o carimbo e o chip. O mesmo hex vale no HTML e no card.

- **Sustentado** (#3dce8f): verdadeiro.
- **Ressalva** (#b7d36a): verdadeiro, mas…
- **Não é bem assim** (#e2b34a): também é a tinta de aviso declarada no shell.
- **Exagerado** (#f0a05a): exagerado e promessa.
- **Distorcido** (#f3a0a8).
- **Contradito** (#ff6b6b): contradito e erro de consulta. O texto de erro do painel usa esta tinta.
- **Sem prova** (#c8c2ba).
- **Em aberto** (#a9bdd4): sem prova pública, versões em disputa, indício, dados incompletos, áudio confuso, sem fonte, inconclusivo e checando.

### Named Rules

**The Coral Ativo Rule.** O coral preenche a seção atual, o botão principal e a seleção de texto, risca os 2px sob o cabeçalho e fecha os quatro lados do card. A placa permanece na noite.

**The Verde ao Vivo Rule.** O verde é o anel de foco, o hover da navegação e a cor de “entrando agora”. O botão principal permanece coral.

## Typography

**Display Font:** Archivo Black (sans-serif)
**Body Font:** Literata (Georgia, serif)

**Character:** Archivo Black chega num único corte, peso 400, e faz o nome, o carimbo, a navegação, o botão e a fala citada. Literata chega em 500 e 700 e faz o texto corrido, o resumo e, no card, quem falou e a fonte. O nome do produto ao lado da marca usa Archivo Black a 1.05rem, com tracking -0.03em.

### Hierarchy

- **Display** (400, clamp(1.8rem, 3.2vw, 2.7rem), line-height 1.05, tracking -0.03em): a primeira fala da leitura. Máximo de 22ch. Aspas fazem parte da fala.
- **Headline** (400, clamp(1.6rem, 3vw, 2.2rem), line-height 1.05, tracking -0.03em): as falas seguintes. Máximo de 28ch.
- **Title** (400, 1rem, line-height 1.55, tracking 0.04em, maiúsculas): título de seção no ao vivo.
- **Body** (1.05rem, line-height 1.55): texto da página. Na leitura, o resumo corre até 70ch. No card, o resumo é Literata 500 a 36px.
- **Label** (400, 0.72rem, tracking 0.04em, maiúsculas): item de navegação e o rótulo “entrando agora”, este com tracking 0.08em e na tinta verde.

### Named Rules

**The Duas Faces Rule.** Archivo Black no peso 400 leva o nome, a navegação, o botão, o carimbo e a fala citada. Literata leva o texto corrido e o resumo; no card, também quem falou e a fonte.

## Layout

O cabeçalho atravessa a página: padding 14px 28px, marca a 48px de altura, navegação em faixa com gap de 8px. Abaixo de 800px o padding lateral cai para 16px e a marca para 36px. Abaixo de 560px a navegação vira grade de três colunas.

O ao vivo centra uma coluna `min(1180px, calc(100% - 32px))`. Checar usa 820px, o placar 1100px, a leitura e o método padding lateral de 40px (16px abaixo de 720px). A leitura não centra uma placa: a fala começa na margem.

O ao vivo parte em duas colunas com gap de 16px, a transcrição mais larga que as checagens, e empilha abaixo de 860px. O placar empilha abaixo de 800px. Gaps recorrentes: 8px entre ações, 10px dentro do compositor, 12px no bloco de controle, 16px entre placas.

### Named Rules

**The Medida de Leitura Rule.** O texto corrido fica entre 62ch e 74ch. A fala citada para em 28ch; a primeira, em 22ch.

## Elevation & Depth

O sistema é plano. `--ie-shadow` é `none`, e a placa do ao vivo declara `box-shadow: none`. A profundidade é tonal: noite, depois placa, depois campo, separadas pela linha de 1px. O cabeçalho não flutua; a faixa coral de 2px o separa da página. O trecho marcado só troca o fundo para o coral lavado.

O foco global é outline de 3px na tinta verde, com offset de 2px. Hover de botão troca a cor na hora, sem duração. A leitura usa scroll suave e desliga isso em `prefers-reduced-motion`.

### Named Rules

**The Placa Lisa Rule.** A sombra do sistema é none. A profundidade é o degrau da noite para a placa e para o campo, com a linha de 1px.

## Shapes

Os cantos são retos. `--ie-radius` e `--ie-radius-sm` são 0px, e placa, campo, botão, navegação e card repetem esse zero.

O carimbo e o chip compartilham a mesma silhueta: preenchimento transparente, borda 3px, outline 1px com offset -6px, Archivo Black em maiúsculas, tracking 0.06em, 0.78rem, padding 5px 10px, `rotate(-2deg)`. A tinta é a do estado. Em `prefers-reduced-motion` a inclinação some.

### Named Rules

**The Canto Reto Rule.** Botão, campo, placa, navegação e card fecham em canto reto. O raio do sistema é 0px.

**The Carimbo Vazado Rule.** O carimbo não tem preenchimento. No HTML, borda de 3px, outline de 1px com offset -6px e rotate(-2deg), na tinta do estado. No card, traço externo de 6px, traço interno de 2px e rotate(-0.045rad). prefers-reduced-motion zera a inclinação do HTML.

## Components

### Buttons

O botão principal é coral com texto noite, Archivo Black em peso 400, tracking 0.03em, padding 10px 14px, borda de 1px na mesma tinta. O rótulo fica em caixa de frase. No hover, fundo e borda passam ao coral claro.

- **Shape:** canto reto (0px)
- **Primary:** coral sobre noite, padding 10px 14px
- **Hover / Focus:** hover no coral claro; foco no outline verde do shell
- **Ghost:** fundo transparente, texto suave, borda na linha. No hover do ao vivo, fundo verde lavado e texto papel

### Chips

O chip é o carimbo. Mesma construção vazada, mesma tinta de estado, mesma inclinação. Não existe chip preenchido.

- **Style:** contorno duplo, fundo transparente, Archivo Black em maiúsculas
- **State:** a classe do estado troca só a tinta

### Cards / Containers

- **Corner Style:** reto (0px)
- **Background:** placa sobre a noite
- **Shadow Strategy:** nenhuma
- **Border:** 1px na linha
- **Internal Padding:** 16px nas placas de checar e do placar; 12px na barra e no compositor do ao vivo; 16px 18px na seção do ao vivo

### Inputs / Fields

Campo, select e textarea herdam Literata, fundo campo, texto papel, caret coral, borda de 1px na linha, padding 10px 12px, canto reto. O placeholder é a meta. No checar o padding do controle sobe para 12px.

- **Style:** linha de 1px, fundo campo, canto reto
- **Focus:** outline verde
- **Error:** texto na tinta de contradito

### Navigation

Faixa noturna com a marca IE e o nome Mentirômetro em Archivo Black. Itens em maiúsculas, 0.72rem, tracking 0.04em, altura mínima 40px, padding 0 12px, borda de 1px na linha, fundo transparente. A seção atual preenche em coral com texto noite e não muda no hover. Os outros itens, no hover, ganham borda e texto verdes. Abaixo de 560px os itens se distribuem em três colunas.

### Carimbo

Assinatura do produto. No HTML é a classe compartilhada com o chip. O aviso AO VIVO da leitura repete a construção vazada, em verde, com tracking 0.08em. No card exportado o carimbo é desenhado no canvas: Archivo Black entre 42px e 26px, traço duplo, inclinação -0.045rad, tinta do estado, sem preenchimento.

### Card de compartilhamento

Arquivo preto de 1080×1350 no feed e 1080×1920 no stories. Padding de conteúdo 88px. Traço coral de 12px insetado 18px nos quatro lados. A marca IE entra pelo arquivo da logo; em seguida MENTIRÔMETRO em Archivo Black 28px na tinta coral, quem falou em Literata 500 a 32px, a fala entre aspas em Archivo Black 64px, o carimbo vazado, o resumo em Literata 500 a 36px, um fio coral de 3px e a fonte em Literata 700 a 28px.

## Do's and Don'ts

### Do:

- **Do** assentar a página na noite e o bloco de trabalho na placa, com borda de 1px na linha.
- **Do** usar coral com texto noite no botão principal e na seção atual.
- **Do** deixar o carimbo vazado, em Archivo Black, maiúsculas, na tinta do estado.
- **Do** usar Literata no resumo e no texto corrido, e Archivo Black na fala citada.
- **Do** gerar o card na noite, com borda coral nos quatro lados, a marca IE e o carimbo vazado.
- **Do** respeitar prefers-reduced-motion, tirando a inclinação do carimbo no HTML.

### Don't:

- **Don't** abrir um quadro claro nem preencher o carimbo como chip.
- **Don't** arredondar cantos nem aplicar drop shadow.
- **Don't** pintar o botão principal de verde nem a placa de coral.
- **Don't** escurecer o hover: o coral do hover é mais claro que o coral de repouso.
- **Don't** copiar o visual do Fato Carimbado.
