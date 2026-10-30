import uuid
from datetime import datetime, timedelta, timezone

import boto3
import requests

API_URL = "https://ultimosismo.igp.gob.pe/api/ultimo-sismo/ajaxb/{anio}"
TABLA = "TablaSismosIGP"
CANTIDAD = 10


def obtener_sismos(anio):
    """Descarga la lista de sismos de un año desde el API JSON del IGP."""
    response = requests.get(
        API_URL.format(anio=anio),
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def a_item(sismo):
    """Convierte un sismo del API en un item para DynamoDB (todo como texto)."""
    item = {
        "codigo": sismo.get("codigo"),
        "fecha_local": (sismo.get("fecha_local") or "")[:10],
        "hora_local": (sismo.get("hora_local") or "")[11:19],
        "referencia": sismo.get("referencia"),
        "magnitud": sismo.get("magnitud"),
        "profundidad": sismo.get("profundidad"),
        "latitud": sismo.get("latitud"),
        "longitud": sismo.get("longitud"),
        "intensidad": sismo.get("intensidad"),
    }
    return {k: str(v) for k, v in item.items() if v not in (None, "")}


def lambda_handler(event, context):
    # Año actual en hora de Lima (UTC-5)
    anio = (datetime.now(timezone.utc) - timedelta(hours=5)).year

    try:
        sismos = obtener_sismos(anio)
        # Si el año recién empezó y hay pocos sismos, completar con el año anterior
        if len(sismos) < CANTIDAD:
            sismos = obtener_sismos(anio - 1) + sismos
    except Exception as e:
        return {
            'statusCode': 502,
            'body': f'Error al acceder al IGP: {str(e)}'
        }

    if not sismos:
        return {
            'statusCode': 404,
            'body': 'No se encontraron sismos'
        }

    # El API entrega del más antiguo al más reciente: ordenar y tomar los 10 últimos
    sismos.sort(key=lambda s: s.get("idlistasismos") or 0, reverse=True)
    filas = [a_item(s) for s in sismos[:CANTIDAD]]

    table = boto3.resource('dynamodb').Table(TABLA)

    # Eliminar todos los elementos de la tabla antes de agregar los nuevos
    scan = table.scan(ProjectionExpression="id")
    items = scan["Items"]
    while "LastEvaluatedKey" in scan:
        scan = table.scan(ProjectionExpression="id",
                          ExclusiveStartKey=scan["LastEvaluatedKey"])
        items.extend(scan["Items"])

    with table.batch_writer() as batch:
        for it in items:
            batch.delete_item(Key={'id': it['id']})

    # Insertar los nuevos datos
    for n, fila in enumerate(filas, start=1):
        fila['#'] = n
        fila['id'] = str(uuid.uuid4())
        table.put_item(Item=fila)

    return {
        'statusCode': 200,
        'body': filas
    }