# Strava Print

Aplicação local em Python para transformar uma atividade GPX em arte para quadro: pôster físico, rota vetorial, arquivos rasterizados em 300 DPI e modelos 3D STL para sobrepor ao papel.

> Strava é uma marca de seus respectivos proprietários. Este projeto não é afiliado nem endossado pela Strava.

## Recursos

- Leitura defensiva de GPX, inclusive múltiplos segmentos, sem elevação e sem timestamps.
- Métricas de distância, duração, movimento estimado, ganho/perda, altitudes, velocidade e ritmo quando os dados permitem.
- Templates configuráveis em JSON: `classic_portrait`, `classic_landscape`, `photo_left_portrait` e `photo_top_portrait`.
- Tema Gallery Edition com composição editorial, peça central simulada e prévia separada do arquivo limpo de impressão.
- Temas Minimal Light, Warm Paper, Dark e Strava Inspired, sem logotipo oficial.
- PDF A4 em tamanho físico real, SVG editável, PNG/JPG 300 DPI e página opcional de calibração.
- Base, rota e modelo combinado em STL. A rota é uma malha tubular contínua, não uma coleção de segmentos soltos.
- Interface Streamlit e CLI sem dependência de mapas externos ou chaves de API.

## Instalação

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
streamlit run strava_print/app.py
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
streamlit run strava_print/app.py
```

## Uso pela interface

Envie um `.gpx`, escolha o layout e edite título, local, atividade, unidades, rotação e largura da rota 3D. Nos layouts Photo, envie JPG, JPEG, PNG ou WEBP. A foto é renderizada com crop `cover`, sem deformação, e seus ajustes ficam no JSON de projeto.

## Uso pela CLI

```bash
python -m strava_print.cli --gpx examples/Morning_Ride.gpx --template classic_portrait --title "Morning Ride" --location "Izumo, Shimane, Japan" --output output/ --stem morning_ride_classic_a4

python -m strava_print.cli --gpx examples/Morning_Ride.gpx --template photo_left_portrait --photo examples/morning_photo.jpg --title "Morning Ride" --output output/ --stem morning_ride_photo_a4
```

Cada execução gera `.pdf`, `.svg`, `.png`, `.jpg`, `*_base.stl`, `*_route.stl`, `*_combined.stl` e `*_project.json`. O GPX real não está no repositório; copie-o para `examples/Morning_Ride.gpx` para executar os comandos acima. `tests/fixtures/sample.gpx` é apenas uma fixture automatizada, não representa uma atividade real.

### Relevo 3D com DEM

Para obter montanhas e vales reais, use um GeoTIFF de elevação (DEM) que cubra toda a atividade. Envie-o na interface ou use a CLI:

```bash
python -m strava_print.cli --gpx examples/Morning_Ride.gpx --dem caminho/para/terreno.tif --terrain-height 8 --template classic_portrait --output output --stem morning_ride_terrain
```

O modo Terrain reprojeta o GPX para o CRS do GeoTIFF, recorta e reamostra o terreno e gera uma base circular fechada de 130 mm. `--terrain-height` controla o exagero vertical na peça, não altera os dados do GPX. Sem DEM, o modo Flat Map continua totalmente offline.

## Impressão e montagem

O preset principal é A4 (210 x 297 mm); templates paisagem usam 297 x 210 mm. Os PNGs A4 são 2480 x 3508 px em 300 DPI. Ao imprimir no konbini, escolha **tamanho real/100%** e desative “ajustar à página” quando o papel corresponder ao arquivo. A página extra no PDF traz um quadrado de 50 mm, linha de 100 mm e círculo de 100 mm para conferência.

Para Canon Selphy, exporte um arquivo menor por um template futuro ou imprima a composição em 100 x 148 mm/cartão postal/4 x 6 in sem redimensionamento automático. A Selphy é apropriada para versões menores; o A4 é mais apropriado ao konbini.

A guia clara no layout Classic corresponde à área ocupada pela peça STL: o padrão de largura da base é 130 mm e pode ser alterado no editor. Imprima base e rota em cores diferentes, depois cole a rota sobre a base e a base sobre o pôster usando a guia.

## Desenvolvimento

```bash
pytest
ruff check .
python -m strava_print.cli --gpx tests/fixtures/sample.gpx --output output --stem sample
```

Limitações da primeira versão: o modo Terrain ainda usa base plana offline; pinos de encaixe estão modelados como opção de projeto, mas não são gerados; presets Selphy serão incluídos como templates dedicados. Dados como calorias, frequência cardíaca, potência e cadência não são inventados.

## Licença

Consulte [LICENSE](LICENSE).
