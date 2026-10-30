import uuid
from datetime import datetime

import boto3
import requests

TABLA = "TablaSismosIGP"
CANTIDAD = 10


def obtener_sismos(anio):
    # Endpoint JSON del IGP (si en el Paso 0 encontraste otra URL, cámbiala aquí)
    url = f"https://ultimosismo.igp.gob.pe/ultimo-sismo/ajaxb/{anio}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict):
        data = data.get("data", [])
    return data


def lambda_handler(event, context):
    anio = datetime.now().year

    try:
        sismos = obtener_sismos(anio)
        # Si el año recién empezó y hay pocos sismos, completar con el año anterior
        if len(sismos) < CANTIDAD:
            sismos = sismos + obtener_sismos(anio - 1)
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

    # Los 10 más recientes (el IGP los entrega del más nuevo al más antiguo)
    ultimos = sismos[:CANTIDAD]

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLA)

    # Eliminar todos los elementos de la tabla antes de agregar los nuevos
    scan = table.scan()
    with table.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(Key={'id': each['id']})

    # Insertar los nuevos datos (todo como texto: DynamoDB no acepta float)
    resultado = []
    for i, sismo in enumerate(ultimos, start=1):
        item = {str(k): str(v) for k, v in sismo.items() if v is not None}
        item['#'] = i
        item['id'] = str(uuid.uuid4())
        table.put_item(Item=item)
        resultado.append(item)

    return {
        'statusCode': 200,
        'body': resultado
    }
