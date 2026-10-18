# Checagem do debate

Painel para ouvir a live do debate da Band e checar frases atribuídas a Lula com fonte pública.

A transcrição segue o áudio com atraso de dezenas de segundos. A checagem devolve um destes estados: com fonte a favor, fontes contrariam, recorte exagerado, sem fonte suficiente ou depende do recorte. Frase sem URL `https` não entra como confirmada nem como derrubada.

Quem fala é inferido pelo texto. Se a autoria não estiver clara, a frase não entra na fila. Dá para colar uma frase manualmente.

## Uso

1. Abra o painel e entre com a senha.
2. Confira o link da live e clique em ouvir.
3. Acompanhe a transcrição e os vereditos. Pare quando o debate acabar: cada trecho de áudio e cada busca gastam crédito da OpenRouter.

Se o YouTube responder “Sign in to confirm you're not a bot”, exporte os cookies da conta logada no formato Netscape (`cookies.txt`) e cole o conteúdo em `YOUTUBE_COOKIES`. O arquivo não entra no git.

## Variáveis

Veja `.env.example`. Segredos ficam só no EasyPanel, não no git.
