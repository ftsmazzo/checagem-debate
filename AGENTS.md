# Regras do projeto

- Repositório privado. Não publicar a transcrição bruta nem os vereditos como matéria sem revisão humana.
- Não gravar `OPENROUTER_API_KEY`, `APP_PASSWORD` ou `DATABASE_URL` no git.
- Veredito `sustentado`, `contradito` ou `exagerado` só permanece se houver pelo menos uma URL `https`. Sem isso, o código rebaixa para `sem_evidencia`.
- Não rotular uma frase como fake. O painel mostra o estado e a fonte.
- A fila automática só checa fala atribuída a Lula. Frase de outro candidato não entra nessa fila.
- A escuta aceita apenas URL dos domínios do YouTube.
- `/health` fica público para monitoramento. O painel não pede senha: o endereço é de uma pessoa só.
- Banco deste projeto é exclusivo. Não apontar `DATABASE_URL` para outro serviço.
