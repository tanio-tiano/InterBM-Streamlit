import google.generativeai as genai
import os

# Reemplaza con tu API KEY o usa tu variable de entorno

genai.configure(api_key='AIzaSyCqaV4EgDDhROzJatL7ivD6IK4OUT8eRf4')

print("Obteniendo modelos disponibles...\n")

try:
    models = genai.list_models()
    for m in models:
        print(f"- {m.name}")
except Exception as e:
    print("ERROR al listar modelos:\n", e)
