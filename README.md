# api-web-scraping-sismos

API serverless que hace Web Scraping a los 10 últimos sismos reportados por el Instituto Geofísico del Perú (IGP) y los almacena en una tabla DynamoDB.

Curso: CS2032 - Cloud Computing (UTEC) - Semana 12, Taller 2: Web Scraping en framework serverless.

## Fuente de datos

La página de reportes sísmicos del IGP (https://ultimosismo.igp.gob.pe/productos/reportes-sismicos) se arma con JavaScript, por lo que el HTML inicial no contiene la tabla. La función consume directamente el API JSON que usa esa página:

```
https://ultimosismo.igp.gob.pe/api/ultimo-sismo/ajaxb/{año}
```

## Arquitectura

- **API Gateway**: `GET /scrape/sismos`
- **AWS Lambda** (Python 3.12): `sismos.lambda_handler`
- **DynamoDB**: tabla `TablaSismosIGP` (clave de partición `id`)

## Archivos

| Archivo | Descripción |
|---|---|
| `sismos.py` | Función Lambda que descarga los sismos, toma los 10 más recientes y los guarda en DynamoDB |
| `serverless.yml` | Configuración del servicio, la función, el endpoint y la tabla DynamoDB |
| `requirements.txt` | Dependencias de Python (`requests`) |
| `.gitignore` | Excluye las librerías instaladas localmente |

## Funcionamiento

1. Descarga la lista de sismos del año actual desde el API del IGP (si hay menos de 10, completa con el año anterior).
2. Ordena los sismos del más reciente al más antiguo y se queda con los 10 primeros.
3. Elimina los elementos anteriores de la tabla `TablaSismosIGP`.
4. Inserta los 10 sismos, cada uno con un `id` único (UUID) y un número de orden `#`.

## Campos guardados

`codigo`, `fecha_local`, `hora_local`, `referencia`, `magnitud`, `profundidad`, `latitud`, `longitud`, `intensidad`.

## Despliegue

```bash
git clone https://github.com/TU_USUARIO/NOMBRE_DEL_REPO.git
cd NOMBRE_DEL_REPO
pip3 install -r requirements.txt -t .
sls deploy
```

Al terminar, Serverless muestra el endpoint:

```
GET - https://<API_ID>.execute-api.us-east-1.amazonaws.com/dev/scrape/sismos
```

## Prueba

```bash
curl https://<API_ID>.execute-api.us-east-1.amazonaws.com/dev/scrape/sismos
```

La respuesta incluye `"statusCode": 200` y la lista de los 10 sismos. Los mismos datos quedan guardados en la tabla `TablaSismosIGP`.
