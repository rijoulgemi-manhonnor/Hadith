import requests
import os
import logging
import random
import re
import hashlib
from datetime import datetime
from pathlib import Path
import json
from groq import Groq

# --- CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialisation de Groq
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
if groq_client:
    logging.info("✅ GroqCloud initialisé")

class AlternativeHadithAPI:
    """API alternative pour les hadiths - Gratuite et fiable"""
    
    # API gratuite de hadiths (trouvée dans les recherches)
    BASE_URL = "https://hadithapi.com/api"
    
    # Motifs d'invocation en arabe
    DUA_PATTERNS = [
        r'اللهم\s+', r'ربنا\s+', r'رب\s+', r'رب\s+[اعزوجل]',
        r'يا\s+رب', r'يا\s+الله', r'اللَّهُمَّ', r'رَبَّنَا',
        r'رَبِّ', r'اغفر\s+لي', r'ارحمنا', r'اهدنا', r'تقبل', r'استجب'
    ]
    
    # Livres disponibles
    BOOKS = [
        "sahih-bukhari", "sahih-muslim", "sunan-abu-dawud",
        "sunan-tirmidhi", "sunan-nasai", "sunan-ibnmajah"
    ]
    
    def __init__(self):
        self.session = requests.Session()
        # Note: Cette API ne nécessite pas de clé pour des usages basiques
        logging.info("✅ Client AlternativeHadithAPI initialisé")
    
    def contains_dua(self, text):
        """Vérifie si le texte contient une invocation"""
        text = text.strip()
        for pattern in self.DUA_PATTERNS:
            if re.search(pattern, text):
                return True
        return False
    
    def get_random_hadith(self):
        """Récupère un hadith aléatoire"""
        url = f"{self.BASE_URL}/hadiths/random"
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data and data.get('status') == 200:
                hadith = data.get('hadith', {})
                return {
                    "hadith_text": hadith.get('hadithArabic', ''),
                    "metadata": {
                        "collection": hadith.get('book', {}).get('name', ''),
                        "number": hadith.get('hadithNumber', ''),
                        "grade": hadith.get('status', 'Sahih')
                    },
                    "success": True
                }
        except Exception as e:
            logging.error(f"Erreur API Hadith: {e}")
        
        return None
    
    def get_hadith_with_dua(self, max_attempts=20):
        """Récupère un hadith contenant une invocation"""
        
        for attempt in range(max_attempts):
            try:
                # Sélectionner un livre aléatoire
                book = random.choice(self.BOOKS)
                page = random.randint(1, 50)
                
                url = f"{self.BASE_URL}/hadiths"
                params = {
                    'book': book,
                    'paginate': 1,
                    'page': page
                }
                
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if data and data.get('hadiths', {}).get('data'):
                    hadiths = data['hadiths']['data']
                    for hadith in hadiths:
                        hadith_text = hadith.get('hadithArabic', '')
                        
                        if self.contains_dua(hadith_text):
                            logging.info(f"✅ Hadith avec invocation trouvé (tentative {attempt+1})")
                            return {
                                "hadith_text": hadith_text,
                                "metadata": {
                                    "collection": hadith.get('book', {}).get('name', book),
                                    "number": hadith.get('hadithNumber', ''),
                                    "grade": hadith.get('status', 'Sahih')
                                },
                                "success": True
                            }
                
                logging.info(f"⏳ Tentative {attempt+1}/{max_attempts}: pas d'invocation, recherche...")
                
            except Exception as e:
                logging.error(f"Erreur tentative {attempt+1}: {e}")
        
        logging.warning(f"⚠️ Aucun hadith avec invocation trouvé après {max_attempts} tentatives")
        return None

class GroqHadithExplainer:
    """Génère des explications de hadiths en arabe"""
    
    def __init__(self, client):
        self.client = client
        self.cache_dir = Path("groq_cache")
        self.cache_dir.mkdir(exist_ok=True)
    
    def generate_explanation(self, hadith_text, metadata):
        """Génère une explication en arabe"""
        cache_key = hashlib.md5(hadith_text[:100].encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if (datetime.now() - datetime.fromisoformat(data['timestamp'])).days < 7:
                    return data['explanation']
        
        prompt = f"""بصفتك متخصصاً في علوم الحديث، اشرح هذا الحديث باللغة العربية فقط:

الحديث: {hadith_text[:500]}...

المعلومات:
- الكتاب: {metadata['collection']}
- الرقم: {metadata['number']}

اكتب:
1. معنى الكلمات الغريبة
2. شرح مختصر للحديث
3. الفوائد المستفادة

200 كلمة كحد أقصى."""
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            explanation = response.choices[0].message.content.strip()
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'timestamp': datetime.now().isoformat(), 'explanation': explanation}, f)
            
            return explanation
        except Exception as e:
            logging.error(f"Erreur Groq: {e}")
            return None


def get_hijri_date():
    """Récupère la date Hijri"""
    try:
        today = datetime.now().strftime("%d-%m-%Y")
        response = requests.get(f"http://api.aladhan.com/v1/gToH?date={today}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()['data']['hijri']
            return f"{data['day']} {data['month']['ar']} {data['year']}"
    except:
        pass
    
    return datetime.now().strftime("%d %B %Y")


def format_telegram_message(hadith_data, hijri_date, groq_explanation=None):
    """Formate le message Telegram en arabe"""
    metadata = hadith_data['metadata']
    
    message = f"""🌙 *حديث الدعاء*

📚 *الكتاب*: {metadata['collection']}
🔢 *الرقم*: {metadata['number']}
⭐ *الدرجة*: {metadata['grade']}
📅 *التاريخ*: {hijri_date}

━━━━━━━━━━━━━━━━

📖 *الحديث:*
{hadith_data['hadith_text']}

━━━━━━━━━━━━━━━━"""

    if groq_explanation:
        message += f"""

📝 *الشرح:*
{groq_explanation}

━━━━━━━━━━━━━━━━"""

    message += """

#حديث #دعاء #أدعية #إسلام #سنة"""
    
    return message


def send_telegram_message(message):
    """Envoie le message Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(
            url,
            data={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown'
            },
            timeout=15
        )
        return response.status_code == 200
    except Exception as e:
        logging.error(f"❌ Erreur envoi: {e}")
        return False


def run():
    """Fonction principale"""
    logging.info("=" * 50)
    logging.info("🚀 Démarrage du Bot Hadith (Version Alternative)")
    logging.info("=" * 50)
    
    # Vérifications
    if not all([GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        logging.error("❌ Clés API manquantes")
        return
    
    # Date
    hijri_date = get_hijri_date()
    logging.info(f"📅 Date: {hijri_date}")
    
    # Récupérer un hadith avec invocation (NOUVELLE API)
    client = AlternativeHadithAPI()
    hadith_data = client.get_hadith_with_dua(max_attempts=20)
    
    if not hadith_data:
        logging.error("❌ Aucun hadith avec invocation trouvé")
        send_telegram_message("⚠️ لم يتم العثور على حديث يحتوي على دعاء اليوم")
        return
    
    logging.info(f"✅ Hadith trouvé: {hadith_data['metadata']['collection']} n°{hadith_data['metadata']['number']}")
    
    # Générer l'explication
    groq_explanation = None
    if groq_client:
        explainer = GroqHadithExplainer(groq_client)
        groq_explanation = explainer.generate_explanation(
            hadith_data['hadith_text'],
            hadith_data['metadata']
        )
        
        if groq_explanation:
            logging.info(f"✅ Explication générée ({len(groq_explanation)} caractères)")
    
    # Envoyer
    message = format_telegram_message(hadith_data, hijri_date, groq_explanation)
    
    if send_telegram_message(message):
        logging.info("✅ Message envoyé avec succès!")
    else:
        logging.error("❌ Échec de l'envoi")
    
    logging.info("=" * 50)


if __name__ == "__main__":
    run()
