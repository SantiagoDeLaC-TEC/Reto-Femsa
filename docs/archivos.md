# Análisis del Formato de los Archivos de Inventarios

Aquí se documenta el formato de los archivos en crudo para evitar tener problemas en Power Query.

## Kardex (Un Archivo por Mes)

* **Nombre de la hoja de interés:** "DETALLE KARDEX"
* **Encabezados:** Inician en la primera fila.
* **Nombres de columnas:** 

    * "PERIODO"
    * "CODIGO"
    * "DESCRIPTOR"
    * "STOCK"
    * "COSTO"
    * "VALORIZACION"
    * "FULCOM"
    * "UNID CONV"
    * "MESES ANTIG."
    * "ALERTA ANTIG."
    * "DIF. VALORIZACIÓN"
    * "ALERTA STOCK"
    * "ALERTA COSTO"
    * "ALERTA CONVERSIÓN"
    * "ALERTA DUPLICADO*"
    * "ESTADO GENERAL"
    * "LINEA"
    * "NOMBRE LINEA"
    * "POLITICA CJE AL 30SEP"

* **Formato de FULCOM:** Fecha
* **Formato de CODIGO:** "SKU_XXXXXX"

## Balanza (Un Archivo por Mes)

* **Nombre de la hoja de interés:** "FCV" (Es la única)
* **Encabezados:** Empiezan en la 6ta fila, y vienen en formato combinado.
* **Columnas:** Las columnas importantes están en la 1ra (Cuenta), 2da (Descripción), 5ta (Débito) y 6ta columna (Crédito).
* **Formato de la cuenta:** "CTA_XXXXXX"

## Tipo de Cambio (Un Solo Archivo)

* **Nombre de la hoja de interés:** "Consulta" (Es la única)
* **Encabezados:** Empiezan en la 10ma fila, aunque el importante es el de la 12da
* **Formato de Fecha:** Fecha
* **Formato de la unidad de cambio:** $1 MXN → CLP