# Matconecta 4.0

Plataforma educacional de matemática com **FastAPI + SQLAlchemy + MySQL/MariaDB + HTML/CSS/JavaScript**.

## O que foi corrigido

- MySQL ou MariaDB nativo como banco oficial; não depende de Docker.
- Instalador Linux idempotente: instala Python/venv e detecta/usa MySQL ou MariaDB, inicia o serviço, cria banco e usuário e gera `.env`.
- Usuário MySQL criado para `localhost` **e** `127.0.0.1`.
- Questões possuem códigos estáveis; o seed não apaga e recria questões a cada execução.
- Tentativas e respostas antigas não são destruídas ao sincronizar conteúdo.
- O gabarito nunca é enviado no endpoint de carregamento das questões.
- A correção e a pontuação são calculadas no backend.
- Senhas usam scrypt e sessões usam tokens aleatórios armazenados apenas como hash no banco.
- Frontend não depende de `localStorage` para dados acadêmicos.
- API possui health check e documentação automática.
- Teoria, exemplos, passos e checklist são exibidos antes do simulado.
- 50 questões de matemática básica + 225 questões dos 15 assuntos do Ensino Médio, sorteadas e embaralhadas a cada simulado (15 questões de base ou 10 por assunto, por vez).

## Instalação recomendada no Ubuntu/Debian + VS Code

Na raiz do projeto:

```bash
./setup_linux.sh
```

Depois:

```bash
./run_linux.sh
```

Abra `http://127.0.0.1:8000`.

Documentação da API: `http://127.0.0.1:8000/docs`.

## Se preferir manualmente

```bash
sudo apt update
sudo apt install -y python3-full python3-venv python3-pip mariadb-server mariadb-client
sudo systemctl enable --now mariadb
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Depois crie o banco/usuário e configure `DATABASE_URL` no `.env`. O instalador automático faz isso de forma segura para ambiente local.

## Segurança

O `.env` contém segredo e não deve ser versionado. Para produção, troque a senha gerada, use HTTPS, cookies seguros ou um mecanismo de sessão apropriado e faça migrations controladas.

## Public/produção com Railway

O projeto já inclui `Procfile` e `railway.toml` com o comando correto para o Railway:

```bash
cd backend && uvicorn backendapi:app --host 0.0.0.0 --port $PORT
```

No serviço da aplicação, configure `DATABASE_URL` apontando para o MySQL do Railway. O backend aceita `mysql://` e normaliza automaticamente para o driver PyMySQL instalado.

Depois gere o domínio público do serviço no Railway. O endpoint de verificação é `/api/health`.

## Teste público temporário com Cloudflare

Para testar o servidor local, mantenha o Matconecta rodando em uma janela e, em outra, execute:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Use exatamente a URL `https://...trycloudflare.com` mostrada pelo `cloudflared` e mantenha o processo aberto. Quick Tunnels são temporários e o endereço pode mudar quando o processo é reiniciado.
