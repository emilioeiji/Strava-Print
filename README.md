# GPX Print Studio

Aplicação Django para transformar atividades GPX em quadros personalizados: editor visual, projetos persistentes, pôster físico, arquivos em 300 DPI e modelos 3D de terreno com rota encaixável. O motor de renderização continua disponível como biblioteca Python e CLI.

> Strava é uma marca de seus respectivos proprietários. Este projeto não é afiliado nem endossado pela Strava.

## Recursos

- Leitura defensiva de GPX, inclusive múltiplos segmentos, sem elevação e sem timestamps.
- Métricas de distância, duração, movimento estimado, ganho/perda, altitudes, velocidade e ritmo quando os dados permitem.
- Templates configuráveis em JSON: `classic_portrait`, `classic_landscape`, `photo_left_portrait` e `photo_top_portrait`.
- Tema Gallery Edition com composição editorial, peça central simulada e prévia separada do arquivo limpo de impressão.
- Mockup de quadro completo, detalhe 3D e acabamentos selecionáveis para material e cor da rota.
- Temas Minimal Light, Warm Paper, Dark e Strava Inspired, sem logotipo oficial.
- PDF A4 em tamanho físico real, SVG editável, PNG/JPG 300 DPI e página opcional de calibração.
- Base, rota e modelo combinado em STL. No modo Terrain, a base recebe um canal e a rota é um inserto contínuo de fundo plano, imprimível sem suportes.
- Dashboard Django responsivo, contas opcionais, projetos por sessão e downloads protegidos.
- Editor comercial com preview montado, configurações de foto, DEM, rota e exportação.
- Pacote ZIP com PDF, SVG, PNG, JPG, JSON e três arquivos STL.
- Pedidos com preço calculado no servidor, entrega, status e histórico.
- Pagamento manual funcional e Stripe Checkout opcional com webhook idempotente.
- Fila de exportação persistente, worker Linux e acompanhamento pelo editor.
- E-mails configuráveis e armazenamento privado local ou S3.
- CLI independente, sem dependência obrigatória de mapas externos ou chaves de API.

## Instalação

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

Ou execute `./start.ps1`.

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

Ou execute `chmod +x start.sh && ./start.sh`. Abra `http://127.0.0.1:8000`.

## Aplicação Django

Na primeira tela, envie um GPX e nomeie o projeto. O editor extrai as métricas, cria a composição inicial e permite alterar textos, layout, tema, unidades, métricas, fotografia, DEM e parâmetros físicos do modelo 3D. **Atualizar visualização** salva o projeto e refaz o mockup; **Gerar pacote completo** produz todos os arquivos de fabricação.

Projetos anônimos pertencem à sessão local do navegador. Uma conta pode ser criada para persistir a autoria e acessar os projetos associados. O admin do Django está disponível em `/admin/` depois de criar um superusuário:

```bash
python manage.py createsuperuser
```

## Uso pela CLI

```bash
python -m strava_print.cli --gpx examples/Morning_Ride.gpx --template classic_portrait --title "Morning Ride" --location "Izumo, Shimane, Japan" --output output/ --stem morning_ride_classic_a4

python -m strava_print.cli --gpx examples/Morning_Ride.gpx --template photo_left_portrait --photo examples/morning_photo.jpg --title "Morning Ride" --output output/ --stem morning_ride_photo_a4
```

Cada execução gera `.pdf`, `.svg`, `.png`, `.jpg`, `*_base.stl`, `*_route.stl`, `*_combined.stl` e `*_project.json`. O GPX real não está no repositório; copie-o para `examples/Morning_Ride.gpx` para executar os comandos acima. `tests/fixtures/sample.gpx` é apenas uma fixture automatizada, não representa uma atividade real.

### Relevo 3D com DEM

Para obter montanhas e vales reais, use um GeoTIFF de elevação (DEM) que cubra toda a atividade. Envie-o na interface ou use a CLI:

```bash
python -m strava_print.cli --gpx examples/Morning_Ride.gpx --dem caminho/para/terreno.tif --terrain-height 8 --terrain-route-style inlay --inlay-clearance 0.15 --template classic_portrait --output output --stem morning_ride_terrain
```

O modo Terrain reprojeta o GPX para o CRS do GeoTIFF, recorta e reamostra o terreno e gera uma base circular fechada de 130 mm. Por padrão, `inlay` recorta um canal na base e gera a rota inteira com fundo plano para impressão direta na mesa. A folga padrão de `0,15 mm` por lado pode ser aumentada para impressoras menos precisas. Use `--terrain-route-style tube` para manter a antiga rota tubular sobre a superfície. `--terrain-height` controla o exagero vertical na peça, não altera os dados do GPX. Sem DEM, o modo Flat Map continua totalmente offline.

## Impressão e montagem

O preset principal é A4 (210 x 297 mm); templates paisagem usam 297 x 210 mm. Os PNGs A4 são 2480 x 3508 px em 300 DPI. Ao imprimir no konbini, escolha **tamanho real/100%** e desative “ajustar à página” quando o papel corresponder ao arquivo. A página extra no PDF traz um quadrado de 50 mm, linha de 100 mm e círculo de 100 mm para conferência.

Para Canon Selphy, exporte um arquivo menor por um template futuro ou imprima a composição em 100 x 148 mm/cartão postal/4 x 6 in sem redimensionamento automático. A Selphy é apropriada para versões menores; o A4 é mais apropriado ao konbini.

A guia clara no layout Classic corresponde à área ocupada pela peça STL: o padrão de largura da base é 130 mm e pode ser alterado no editor. Imprima `base.stl` apoiado pela face plana e `route.stl` com o fundo plano na mesa, em cores diferentes. Pressione a rota no canal e use uma pequena quantidade de cola apenas depois de confirmar o encaixe. O `combined.stl` serve como referência montada ou para impressão multimaterial.

## Desenvolvimento

```bash
python -m pytest -q
python -m ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python -m strava_print.cli --gpx tests/fixtures/sample.gpx --output output --stem sample
```

O Streamlit anterior foi mantido somente como interface legada. Para utilizá-lo:

```bash
pip install -e ".[legacy]"
streamlit run strava_print/app.py
```

## Deploy Linux com Apache e MariaDB

O deploy de produção foi preparado para ambiente virtual, Apache `mod_wsgi` e MariaDB. SQLite continua disponível somente para desenvolvimento. As configurações são lidas do ambiente, de `.env` no diretório do projeto ou, preferencialmente em produção, de `/etc/strava-print.env`.

Em Ubuntu/Debian, instale os pacotes do sistema:

```bash
sudo apt update
sudo apt install apache2 libapache2-mod-wsgi-py3 mariadb-server \
  python3-venv python3-dev build-essential pkg-config default-libmysqlclient-dev
```

Crie o banco com UTF-8 e um usuário exclusivo:

```sql
CREATE DATABASE strava_print CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'strava_print'@'localhost' IDENTIFIED BY 'troque-esta-senha';
GRANT ALL PRIVILEGES ON strava_print.* TO 'strava_print'@'localhost';
FLUSH PRIVILEGES;
```

Instale o projeto no servidor:

```bash
sudo mkdir -p /var/www/strava-print
sudo chown "$USER":www-data /var/www/strava-print
git clone https://github.com/emilioeiji/Strava-Print.git /var/www/strava-print
cd /var/www/strava-print
git switch feat/django-commercial-studio
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[production]"
```

Copie `.env.example` para `/etc/strava-print.env`, defina permissão `640` e preencha pelo menos:

```dotenv
DJANGO_SECRET_KEY=gere-uma-chave-longa-e-aleatoria
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=quadros.exemplo.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://quadros.exemplo.com
DB_NAME=strava_print
DB_USER=strava_print
DB_PASSWORD=troque-esta-senha
DB_HOST=127.0.0.1
DB_PORT=3306
EXPORT_JOBS_INLINE=0
```

Senhas com caracteres especiais não precisam ser codificadas quando as variáveis `DB_*` são usadas. Depois, prepare banco, estáticos e permissões:

```bash
sudo chown root:www-data /etc/strava-print.env
sudo chmod 640 /etc/strava-print.env
source .venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
sudo mkdir -p media
sudo chown -R www-data:www-data media
```

O `check --deploy` pode recomendar HSTS para subdomínios e preload. Ative `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` e `DJANGO_SECURE_HSTS_PRELOAD` somente quando todos os subdomínios estiverem definitivamente disponíveis por HTTPS.

### Apache mod_wsgi

Edite os domínios e caminhos de certificado em `deploy/apache-strava-print.conf.example`, copie para `/etc/apache2/sites-available/strava-print.conf` e habilite o site:

```bash
sudo a2enmod wsgi ssl headers rewrite
sudo a2ensite strava-print.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

O exemplo usa `mod_wsgi` em modo daemon e serve `/static/` diretamente pelo Apache. O diretório `media/` não é publicado: GPX, fotos e exports continuam passando pelas views autenticadas. A resposta `{"status":"ok"}` em `https://seu-dominio/health/` confirma a aplicação.

### Worker systemd

O Apache atende a interface e um serviço separado processa os exports. Copie `deploy/strava-print-worker.service.example` para `/etc/systemd/system/strava-print-worker.service`:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now strava-print-worker
sudo systemctl status strava-print-worker
journalctl -u strava-print-worker -f
```

Após cada atualização do código, ative o venv, instale dependências, execute `migrate` e `collectstatic`, então reinicie Apache e worker. Revise também a [checklist oficial de deploy do Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

### Pagamentos Stripe

Instale as dependências de produção e configure:

```bash
pip install -e ".[production]"
export STRIPE_SECRET_KEY="sk_live_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
```

Cadastre no Stripe o endpoint `https://seu-dominio/integracoes/stripe/webhook/` para `checkout.session.completed`, `checkout.session.async_payment_succeeded` e `checkout.session.async_payment_failed`. O pedido só é marcado como pago pelo webhook assinado; o retorno do navegador não libera produção. Consulte a [documentação de fulfillment](https://docs.stripe.com/checkout/fulfillment).

Sem Stripe, **Combinar pagamento** permanece disponível. Edite `MANUAL_PAYMENT_INSTRUCTIONS` com os dados e o processo real da empresa.

### E-mail e S3

Defina `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` e `DEFAULT_FROM_EMAIL`. Em desenvolvimento, os e-mails aparecem no terminal. Para armazenamento privado S3:

```bash
export AWS_STORAGE_BUCKET_NAME="seu-bucket-privado"
export AWS_S3_REGION_NAME="ap-northeast-1"
```

Use uma credencial IAM de privilégio mínimo fornecida ao processo por role ou variáveis seguras; não coloque chaves no Git. Downloads continuam passando pelas views autorizadas.

### Retenção e backup

Simule e aplique a remoção de projetos sem pedidos após 90 dias:

```bash
python manage.py cleanup_projects --days 90 --dry-run
python manage.py cleanup_projects --days 90
```

Faça backup diário do MariaDB e do storage. Projetos vinculados a pedidos são protegidos da limpeza automática. Um exemplo de backup é `mariadb-dump --single-transaction strava_print > strava_print.sql`.

## Estrutura

- `strava_print/`: motor de GPX, layout, renderização e STL.
- `strava_print_web/`: configuração do projeto Django.
- `studio/`: modelos, formulários, serviços, views, assets e migrações.
- `web_templates/`: dashboard, editor e autenticação.
- `templates/`: configurações físicas dos layouts de impressão.
- `media/`: uploads e exportações locais, ignorados pelo Git.

Limitações da primeira versão: operações de encaixe aumentam a quantidade de faces do STL; pinos de encaixe estão modelados como opção de projeto, mas não são gerados; presets Selphy serão incluídos como templates dedicados. Dados como calorias, frequência cardíaca, potência e cadência não são inventados.

## Licença

Consulte [LICENSE](LICENSE).
