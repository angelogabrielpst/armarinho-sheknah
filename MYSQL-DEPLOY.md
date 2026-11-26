# Deploy na Vercel com MySQL

A Vercel publica o site estático e as funções Python sob o mesmo domínio. As rotas em `api/` são mapeadas automaticamente para `/api/...`; `app-config.js` deve continuar com `apiBaseUrl` vazio.

## Banco de dados

A Vercel não fornece um MySQL próprio. No Marketplace da Vercel, a integração TiDB Cloud oferece compatibilidade com o protocolo MySQL. Você também pode conectar outro MySQL externo.

1. Importe este repositório na Vercel usando a integração com GitHub.
2. No Marketplace da Vercel, adicione TiDB Cloud (ou o provedor MySQL que você usa) ao projeto e crie o banco e usuário.
3. Em Settings > Environment Variables do projeto Vercel, configure `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD` e `MYSQL_DATABASE` com os valores fornecidos pelo banco. O backend também reconhece os nomes `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD` e `MYSQLDATABASE`.
4. Configure `ADMIN_PASSWORD` com uma senha forte e `ADMIN_TOKEN_SECRET` com um segredo aleatório longo. Não coloque esses valores em arquivos do repositório nem os envie pelo chat.

Na primeira chamada da API, o backend cria as tabelas e inclui os oito produtos iniciais e o WhatsApp padrão. A conexão MySQL é obrigatória na Vercel; SQLite fica apenas para desenvolvimento local.

## Imagens

O disco das funções Vercel não é persistente. No dashboard, crie um Vercel Blob Store público e conecte-o a este projeto. A Vercel fornece as credenciais OIDC automaticamente. O backend salva as imagens no Blob e grava a URL pública no MySQL.

## Publicação

Depois de importar o repositório, a Vercel faz deploy automático a cada push para `main`. O workflow de GitHub Pages está desativado; o domínio Vercel serve tanto o site quanto as rotas da API.

## Desenvolvimento local

Com `app-config.js` vazio, rode `python server.py` e abra `http://localhost:8000`. Sem `MYSQL_HOST`, o backend usa `papelaria.db` local e guarda as imagens em `uploads/`. Os dados personalizados desse SQLite não são copiados automaticamente para o MySQL remoto.
