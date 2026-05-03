import requests
from bs4 import BeautifulSoup
import datetime
import re
import time
import json
import os

URL_LISTA = [
    "https://www.kaypahoito.fi/hoi50110",
    "https://www.kaypahoito.fi/hoi50117",
    "https://www.kaypahoito.fi/hoi50127",
    "https://www.kaypahoito.fi/hoi50094",
    "https://www.kaypahoito.fi/hoi50090",
    "https://www.kaypahoito.fi/hoi50086",
    "https://www.kaypahoito.fi/hoi50057",
    "https://www.kaypahoito.fi/hoi07025",
    "https://www.kaypahoito.fi/hoi40020",
    "https://www.kaypahoito.fi/hoi50074"
]

HISTORY_FILE = "historia.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def lataa_historia():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def tallenna_historia(data):
    historia = {item['url']: {'pvm': item['pvm'], 'tila': item['tila']} for item in data if item['pvm'] != "VIRHE"}
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(historia, f, ensure_ascii=False, indent=4)

def hae_tiedot():
    print(f"--- Tarkistus käynnissä: {datetime.datetime.now().strftime('%H:%M:%S')} ---")
    vanha_data = lataa_historia()
    uudet_tulokset = []

    for i, url in enumerate(URL_LISTA, 1):
        try:
            print(f"[{i}/{len(URL_LISTA)}] Haetaan: {url}...")
            time.sleep(0.8)
            res = requests.get(url, headers=HEADERS, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 1. Hae otsikko
            title = "Nimetön suositus"
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)

            # 2. Hae metadata-alue (tarkempi haku kuin koko sivun teksti)
            # Käypä hoito -sivuilla julkaisutiedot ovat usein tietyssä divissä, 
            # mutta get_text on varmempi jos etsitään tietyillä avainsanoilla.
            content = soup.get_text(" ", strip=True)

            # 3. PVM-haku
            pvm = "Ei löytynyt"
            pvm_match = re.search(r"Julkaistu:\s*(\d{2}\.\d{2}\.\d{4})", content)
            if pvm_match:
                pvm = pvm_match.group(1)

            # 4. TILA-haku (KORJATTU: ottaa vain ensimmäisen sanan tai rajoitetun pätkän)
            tila = "Voimassa"
            # Etsitään "Tila:" ja napataan seuraava sana (\S+ tarkoittaa ei-tyhjää merkkiä)
            tila_match = re.search(r"Tila:\s*(\S+)", content)
            if tila_match:
                tila_raw = tila_match.group(1).strip()
                # Puhdistetaan mahdolliset pilkut tai pystyviivat perästä
                tila = re.sub(r'[^\wäöåÄÖÅ]', '', tila_raw)

            # Vertailu
            muutos = False
            if url in vanha_data:
                if vanha_data[url]['pvm'] != pvm or vanha_data[url]['tila'].lower() != tila.lower():
                    muutos = True

            # Uutuus-liekki
            huutomerkki = ""
            if pvm != "Ei löytynyt":
                try:
                    d = datetime.datetime.strptime(pvm, "%d.%m.%Y")
                    if (datetime.datetime.now() - d).days <= 14:
                        huutomerkki = " 🔥"
                except: pass

            uudet_tulokset.append({
                'title': title, 'url': url, 'pvm': pvm, 'tila': tila, 
                'huutomerkki': huutomerkki, 'muutos': muutos
            })

        except Exception as e:
            print(f"   Virhe: {e}")
            uudet_tulokset.append({
                'title': "Yhteysvirhe", 'url': url, 'pvm': "VIRHE", 'tila': "KATKO", 
                'huutomerkki': "⚠️", 'muutos': False
            })

    tallenna_historia(uudet_tulokset)
    luo_html(uudet_tulokset)

def luo_html(data):
    pvm_nyt = datetime.datetime.now().strftime('%d.%m.%Y klo %H:%M')
    muutoksia = sum(1 for x in data if x['muutos'])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="fi">
    <head>
        <meta charset="UTF-8">
        <title>Suun terveyden monitori</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 font-sans p-4 md:p-8">
        <div class="max-w-4xl mx-auto">
            {f'<div class="bg-red-600 text-white p-4 rounded-lg mb-6 shadow-lg text-center font-bold animate-pulse">⚠️ {muutoksia} SUOSITUSTA MUUTTUNUT!</div>' if muutoksia > 0 else ''}
            
            <div class="bg-white shadow-xl rounded-2xl overflow-hidden">
                <div class="bg-slate-800 p-6 text-white flex justify-between items-center">
                    <h1 class="text-xl font-bold uppercase tracking-tight">Käypä hoito - Seuranta</h1>
                    <span class="text-xs text-slate-400 font-mono">{pvm_nyt}</span>
                </div>
                <table class="w-full">
                    <thead class="bg-slate-50 border-b border-slate-200 text-[10px] uppercase text-slate-500">
                        <tr>
                            <th class="p-4 text-left">Suositus</th>
                            <th class="p-4 text-left">Julkaistu</th>
                            <th class="p-4 text-center">Tila</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
    """
    for r in data:
        tila_color = "bg-emerald-100 text-emerald-700"
        if "päivityksessä" in r['tila'].lower(): tila_color = "bg-orange-100 text-orange-700 font-bold"
        elif r['tila'] == "KATKO": tila_color = "bg-red-100 text-red-700"

        html += f"""
                        <tr class="{'bg-red-50' if r['muutos'] else 'hover:bg-slate-50'}">
                            <td class="p-4">
                                <a href="{r['url']}" target="_blank" class="text-blue-600 font-bold hover:underline">
                                    {r['title']} {r['huutomerkki']}
                                </a>
                                { '<span class="ml-2 text-[9px] bg-red-600 text-white px-1.5 py-0.5 rounded font-black italic">MUUTOS!</span>' if r['muutos'] else '' }
                            </td>
                            <td class="p-4 text-sm text-slate-500 font-mono">{r['pvm']}</td>
                            <td class="p-4 text-center">
                                <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold border {tila_color}">
                                    {r['tila']}
                                </span>
                            </td>
                        </tr>
        """
    html += "</tbody></table></div></div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)
    print("Valmis! index.html päivitetty.")

if __name__ == "__main__":
    hae_tiedot()