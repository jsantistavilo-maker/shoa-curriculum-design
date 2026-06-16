"""Descarga el logo de SHOA desde shoa.cl para usar en el dashboard."""
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def descargar_logo() -> bool:
    Path("assets").mkdir(exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get("https://www.shoa.cl", headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")
        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "").lower()
            if "logo" in src.lower() or "logo" in alt:
                url_logo = (
                    src if src.startswith("http")
                    else "https://www.shoa.cl/" + src.lstrip("/")
                )
                img_data = requests.get(url_logo, headers=headers, timeout=10).content
                Path("assets/logo_shoa.png").write_bytes(img_data)
                print("✅ Logo descargado en assets/logo_shoa.png")
                return True
        print("⚠️  No se encontró logo en shoa.cl — coloca el logo manualmente en assets/logo_shoa.png")
    except Exception as e:
        print(f"⚠️  No se pudo descargar logo: {e}")
        print("     Coloca el logo manualmente en assets/logo_shoa.png")
    return False


if __name__ == "__main__":
    descargar_logo()
