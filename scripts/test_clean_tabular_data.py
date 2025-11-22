import sys
import os
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from logic.clean_dataframe import clean_tabular_data

# Use the spreadsheet_content sample provided by the user (trimmed to relevant rows)
spreadsheet_content = [
    ['Nº ', 'TIPO DE GASTO', 'TIPO DE INGRESO', 'ESTADO', 'MONTO INGRESO', 'MONTO GASTO', '"SALDO"', 'FECHA DE PAGO PROYECTADO', 'FECHA DE PAGO EFECTIVA', 'DESCRIPCION', 'CUENTA EMISORA DINEROS', 'CUENTA RECEPTOR', 'FORMA DE PAGO', 'RESPONSABLE DE LA GESTIÓN', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
    ['MES', 'ENERO', '', '', ' Total ingreso efectuado ', 'Total gasto efectuado', '', ' Total gasto pendiente ', '', '', ' INICIO SALDO MES ', ' Total gasto mes ', ' Total ingreso ', ' Saldo mes ', '', '', '', '', '', '', ''],
    ['Fecha Inicio', '01-01-25', '', '', '$2.526.600', '$3.554.853', '', ' $ - ', '', '', '$1.054.389', '$3.554.853', '$2.526.600', '-$1.028.253', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', 'CAJA CHICA MES', '', '', '', ''],
    ['Nº ', 'TIPO DE GASTO', 'TIPO DE INGRESO', 'ESTADO', 'MONTO INGRESO', 'MONTO GASTO', '"SALDO"', 'FECHA DE PAGO PROYECTADO', 'FECHA DE PAGO EFECTIVA', 'DESCRIPCION', 'CUENTA EMISORA DINEROS', 'CUENTA RECEPTOR', 'FORMA DE PAGO', 'RESPONSABLE DE LA GESTIÓN', '', '', 'FECHA', 'DESCRIPCION', 'INGRESO', 'GASTO', 'SALDO'],
    ['1', 'RR.HH.', '', 'PAGADO', '', '$250.000', '', '5/01/2025', '-', 'SUELDO ENTRENADOR CATEGORIA ADULTO ', 'SCOTIABANK', 'JOAQUIN VILLANUEVA', 'TRF', 'LUCCIANO CÁCERES', '', '', '09/01/2024', 'VIATICO VICHO Y FELIPAZO', '', '$40.000', ''],
    ['2', 'RR.HH.', '', 'PAGADO', '', '$390.000', '', '5/01/2025', '-', 'SUELDO ENTRENADOR - INFANTIL, JUVENIL V. Y CADETE Damas Y Varones', 'SCOTIABANK', 'RODRIGO ARECHAVALETA', 'TRF', 'LUCCIANO CÁCERES', '', '', '', '', '', '', ''],
    ['3', 'RR.HH.', '', 'PAGADO', '', '$90.000', '', '5/01/2025', '-', 'SUELDO ENTRENADOR INFANTIL DAMAS', 'SCOTIABANK', 'VICENTE REYES', 'TRF', 'LUCCIANO CÁCERES', '', '', '', '', '', '', ''],
]

res = clean_tabular_data(spreadsheet_content)
print(json.dumps(res, indent=2, ensure_ascii=False))
