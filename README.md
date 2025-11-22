# InterBM Streamlit

Pequeña app en Streamlit que lee datos desde Google Sheets y usa Gemini (Google Generative AI).

## Configuración local (.env)

Crea un archivo `.env` en la raíz del proyecto (ya existe un ejemplo). No subas este archivo al repositorio.

Ejemplo de `.env`:

```env
# Tu API key de Gemini (Google Generative AI)
GOOGLE_API_KEY=tu_api_key_de_gemini_aqui

# (Opcional) API key de desarrollo para CI en la rama `develop`
DEV_GOOGLE_API_KEY=tu_api_key_dev_aqui
```

Asegúrate de que `.env` esté incluido en `.gitignore` (ya lo está).

## Dependencias

Instala las dependencias con:

```powershell
pip install -r .\requirements.txt
```

## Ejecutar la app

```powershell
streamlit run .\app.py
```

## Git / Branches

- Rama principal remota: `origin/main` (renombrada desde `master`). Se creó y subió también la rama `develop`.
- Los workflows de CI están en `.github/workflows/`:
  - `ci-dev.yml` se dispara en pushes/pull requests a `develop`.
  - `ci-prod.yml` se dispara en pushes a `master`.

## Notas sobre secretos

- Mantén tus claves en local dentro de `.env` y no las subas aquí.
- Si prefieres usar GitHub Actions con secretos, puedes añadir `GOOGLE_API_KEY` y `DEV_GOOGLE_API_KEY` en `Settings → Secrets` del repo. No lo hago automáticamente desde este script.

## Recursos útiles

- Crear/gestionar repo desde terminal: usar `gh` (GitHub CLI):

```powershell
# autenticar
gh auth login --web
# crear repo (ejemplo ya ejecutado para este proyecto)
gh repo create InterBM-Streamlit --private --source=. --remote=origin --push
```

Si necesitas que haga más cambios (renombrar `master`→`main`, añadir deploy steps, o configurar secretos), dime y lo implemento.