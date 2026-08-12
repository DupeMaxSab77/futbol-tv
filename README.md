# FutbolTV - Cliente de Escritorio

## Instalación

### Opción 1: Paquete .deb (recomendado)
```bash
sudo dpkg -i futbol-tv_1.0.0_all.deb
```

### Opción 2: Ejecutar directamente
```bash
# Instalar dependencias
sudo apt install python3 python3-pyqt5 python3-requests mpv

# Ejecutar
python3 main.py
```

## Configuración del servidor

Por defecto la app se conecta a `localhost:8000`. Para cambiarlo:

```bash
# Opción 1: Variable de entorno
export FUTBOLTV_SERVER="https://tudominio.com"
futbol-tv

# Opción 2: Editar config.py
SERVER_URL = "https://tudominio.com"
```

## Uso

1. Iniciar la app: `futbol-tv` o `python3 main.py`
2. La app muestra los partidos del día
3. Buscar partido con el filtro
4. Hacer clic en "▶ Ver" para reproducir
5. Si hay múltiples canales, seleccionar uno del dropdown

## Controles del player (mpv)

- `Espacio`: Pausar/Reanudar
- `f`: Pantalla completa
- `q`: Cerrar player
- `←` `→`: Adelantar/Retroceder 10s
- `↑` `↓`: Volumen
- `m`: Silenciar

## Desinstalar

```bash
sudo dpkg -r futbol-tv
```
