import os
import requests
import logging
import random
from datetime import datetime
from pathlib import Path
import time
import json
from groq import Groq

# --- CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HADITH_API_KEY = os.getenv("HADITH_API_KEY")

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Initialisation de Groq
groq_client = None
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        logging.info("✅ Client GroqCloud initialisé avec succès")
    except Exception as e:
        logging.error(f"❌ Erreur initialisation Groq: {e}")
        groq_client = None
else:
    logging.warning("⚠️ Clé GroqCloud manquante dans les variables d'environnement")


class GroqHadithExplainer:
    """
    Utilise GroqCloud pour générer des explications de hadiths
    """
    
    # Modèles disponibles sur GroqCloud
    MODELS = {
        "llama": "llama-3.3-70b-versatile",      # Recommandé pour la qualité
        "mixtral": "mixtral-8x7b-32768",          # Bon rapport performance/prix
        "gemma": "gemma2-9b-it",                   # Plus léger et rapide
        "deepseek": "deepseek-r1-distill-llama-70b" # Pour le raisonnement
    }
    
    def __init__(self, client, model="llama"):
        self.client = client
        self.model_name = self.MODELS.get(model, self.MODELS["llama"])
        self.cache_dir = Path("groq_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.available = client is not None
        
        if self.available:
            logging.info(f"🤖 Explainer Groq initialisé avec modèle: {model} ({self.model_name})")
    
    def generate_explanation(self, hadith_text, metadata, language="fr"):
        """
        Génère une explication du hadith avec GroqCloud
        """
        if not self.available:
            logging.warning("Groq non disponible, pas d'explication générée")
            return None
        
        try:
            # Vérifier le cache d'abord
            cache_key = self._get_cache_key(hadith_text[:100] + language)
            cached = self._get_cached(cache_key)
            if cached:
                logging.info("✅ Explication trouvée dans le cache Groq")
                return cached
            
            # Construire le prompt
            prompt = self._build_prompt(hadith_text, metadata, language)
            
            logging.info(f"🤖 Appel GroqCloud avec modèle: {self.model_name}")
            
            # Appel à l'API Groq
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "Tu es un expert en sciences du hadith. Tu fournis des explications authentiques et détaillées des hadiths en français."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800,
                top_p=0.95
            )
            
            if response and response.choices:
                explanation = response.choices[0].message.content.strip()
                self._save_cache(cache_key, explanation)
                logging.info(f"✅ Explication Groq générée ({len(explanation)} caractères)")
                return explanation
            else:
                logging.error("Réponse Groq vide")
                return None
                
        except Exception as e:
            logging.error(f"Erreur GroqCloud: {e}")
            return None
    
    def _build_prompt(self, hadith_text, metadata, language):
        """
        Construit le prompt pour Groq
        """
        collection = metadata.get('collection', '')
        number = metadata.get('number', '')
        grade = metadata.get('grade', '')
        
        # Limiter la longueur du hadith pour éviter les timeouts
        short_hadith = hadith_text[:500] + "..." if len(hadith_text) > 500 else hadith_text
        
        if language == "fr":
            return f"""En tant qu'expert en sciences du hadith, fournis une explication complète et authentique de ce hadith en français.

Hadith (en arabe) : {short_hadith}

Informations contextuelles :
- Livre : {collection}
- Numéro du hadith : {number}
- Degré d'authenticité : {grade}

Instructions pour l'explication :
1. 📖 **Traduction** : Donne d'abord une traduction fidèle en français
2. 📚 **Contexte** : Explique le contexte (Asbab Al-Wurud) si pertinent
3. 💡 **Explication détaillée** : Développe le sens et les enseignements du hadith
4. ⚖️ **Points juridiques** : Mentionne les règles (fiqh) qui en découlent
5. 🌟 **Leçons à tirer** : Applications pratiques dans la vie quotidienne

Format souhaité :
- Style clair et pédagogique
- Maximum 300 mots
- Divisé en sections avec des émojis

L'explication doit être fidèle à la compréhension des pieux prédécesseurs (Salaf)."""
        
        elif language == "ar":
            return f"""بصفتك متخصصاً في علوم الحديث، اقدم شرحاً وافياً وموثوقاً لهذا الحديث باللغة العربية.

الحديث : {short_hadith}

معلومات إضافية :
- الكتاب : {collection}
- رقم الحديث : {number}
- درجة الحديث : {grade}

تعليمات الشرح :
1. 📖 **ترجمة** : اشرح معاني الكلمات الغريبة
2. 📚 **السياق** : وضح سبب ورود الحديث إن أمكن
3. 💡 **الشرح التفصيلي** : حلل معاني الحديث ومقاصده
4. ⚖️ **الأحكام** : استخرج الفوائد الفقهية
5. 🌟 **الدروس المستفادة** : بين التطبيقات العملية

الصيغة المطلوبة :
- أسلوب واضح ومنهجي
- 300 كلمة كحد أقصى
- مقسم إلى أقسام مع رموز تعبيرية

يجب أن يكون الشرح مطابقاً لفهم السلف الصالح."""
        
        else:  # English
            return f"""As a hadith scholar, provide a comprehensive and authentic explanation of this hadith in English.

Hadith (Arabic) : {short_hadith}

Context :
- Book : {collection}
- Hadith number : {number}
- Authenticity grade : {grade}

Explanation instructions :
1. 📖 **Translation** : First provide an accurate English translation
2. 📚 **Context** : Explain the circumstances (Asbab Al-Wurud) if relevant
3. 💡 **Detailed explanation** : Elaborate the meaning and teachings
4. ⚖️ **Jurisprudential points** : Mention derived rulings (fiqh)
5. 🌟 **Lessons** : Practical applications in daily life

Format :
- Clear and educational style
- Maximum 300 words
- Divided into sections with emojis

The explanation must adhere to the understanding of the pious predecessors (Salaf)."""
    
    def _get_cache_key(self, text):
        """Génère une clé de cache"""
        import hashlib
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_cached(self, key):
        """Récupère du cache"""
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Cache valide 7 jours
                    cached_time = datetime.fromisoformat(data['timestamp'])
                    if (datetime.now() - cached_time).days < 7:
                        return data['explanation']
            except:
                pass
        return None
    
    def _save_cache(self, key, explanation):
        """Sauvegarde dans le cache"""
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'explanation': explanation
                }, f, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Erreur sauvegarde cache: {e}")


class HadeethEncAPI:
    """Client pour l'API HadeethEnc.com"""
    
    BASE_URL = "https://hadeethenc.com/api/v1"
    
    def __init__(self):
        self.session = requests.Session()
    
    def get_random_hadith(self, language="ar"):
        """Récupère un hadith aléatoire"""
        try:
            params = {
                "language": language,
                "random": "true"
            }
            
            random_url = f"{self.BASE_URL}/hadiths/random"
            response = self.session.get(random_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or not data.get('data'):
                return None
            
            hadith_data = data['data']
            hadith_id = hadith_data.get('id')
            
            # Récupérer les détails complets
            details = self.get_hadith_details(hadith_id, language)
            
            if details:
                return details
            else:
                return self._extract_hadith_data(hadith_data)
                
        except Exception as e:
            logging.error(f"Erreur HadeethEnc: {e}")
            return None
    
    def get_hadith_details(self, hadith_id, language="ar"):
        """Récupère les détails complets"""
        try:
            details_url = f"{self.BASE_URL}/hadiths/{hadith_id}"
            params = {"language": language}
            
            response = self.session.get(details_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data and data.get('data'):
                return self._extract_hadith_data(data['data'], detailed=True)
            
        except Exception as e:
            logging.error(f"Erreur détails: {e}")
        
        return None
    
    def _extract_hadith_data(self, data, detailed=False):
        """Extrait les données du hadith"""
        try:
            hadith_text = data.get('hadith', {}).get('content', '')
            if not hadith_text:
                hadith_text = data.get('content', '')
            
            # Explication (si disponible)
            original_explanation = ""
            if detailed:
                original_explanation = data.get('explanation', {}).get('content', '')
            
            # Métadonnées
            collection = data.get('collection', {})
            grade = data.get('grade', {})
            
            metadata = {
                "id": data.get('id'),
                "title": data.get('title', ''),
                "collection": collection.get('name', ''),
                "collection_en": collection.get('en_name', ''),
                "number": data.get('number', ''),
                "grade": grade.get('name', ''),
                "grade_en": grade.get('en_name', ''),
                "narrator": data.get('narrator', {}).get('name', ''),
                "source": "HadeethEnc.com",
                "has_original_explanation": bool(original_explanation and original_explanation.strip())
            }
            
            return {
                "hadith_text": hadith_text,
                "original_explanation": original_explanation,
                "metadata": metadata,
                "success": True
            }
            
        except Exception as e:
            logging.error(f"Erreur extraction: {e}")
            return None


def get_hijri_date():
    """Récupère la date Hijri"""
    try:
        today = datetime.now().strftime("%d-%m-%Y")
        response = requests.get(
            f"http://api.aladhan.com/v1/gToH?date={today}", 
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()['data']['hijri']
        date_ar = f"{data['day']} {data['month']['ar']} {data['year']}"
        date_fr = f"{data['day']} {data['month']['en']} {data['year']}"
        
        return date_ar, date_fr
        
    except Exception as e:
        logging.error(f"Erreur date: {e}")
        now = datetime.now()
        return now.strftime("%d %B %Y"), now.strftime("%d %B %Y")


def fallback_get_hadith():
    """Fallback sur HadithAPI.com"""
    try:
        if not HADITH_API_KEY:
            logging.error("Clé API Hadith manquante")
            return None
        
        random.seed(int(datetime.now().strftime("%Y%m%d")))
        page = random.randint(1, 30)
        
        url = f"https://hadithapi.com/api/hadiths?apiKey={HADITH_API_KEY}&book=sahih-bukhari&paginate=1&page={page}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('hadiths', {}).get('data'):
            hadiths = data['hadiths']['data']
            hadith_index = random.randint(0, len(hadiths) - 1)
            selected = hadiths[hadith_index]
            
            hadith_text = selected.get('hadithArabic', '')
            hadith_number = selected.get('hadithNumber', '')
            
            metadata = {
                "collection": "صحيح البخاري",
                "collection_en": "Sahih Bukhari",
                "number": hadith_number,
                "grade": "صحيح",
                "grade_en": "Sahih",
                "source": "HadithAPI.com",
                "has_original_explanation": False
            }
            
            return {
                "hadith_text": hadith_text,
                "original_explanation": "",
                "metadata": metadata,
                "success": True
            }
            
    except Exception as e:
        logging.error(f"Erreur fallback: {e}")
    
    return None


def format_telegram_message(hadith_data, hijri_date, gregorian_date, groq_explanation=None):
    """
    Formate le message Telegram
    """
    hadith_text = hadith_data['hadith_text']
    original_explanation = hadith_data.get('original_explanation', '')
    metadata = hadith_data['metadata']
    
    # En-tête
    header = f"🌙 *حديث اليوم* | *Hadith du Jour*\n\n"
    
    # Source du hadith
    source_emoji = "🔵" if metadata['source'] == "HadeethEnc.com" else "🟠"
    header += f"{source_emoji} *المصدر* | *Source* : {metadata['source']}\n"
    
    # Source de l'explication
    if groq_explanation:
        header += f"⚡ *شرح* | *Explanation* : GroqCloud (Llama 3.3)\n"
    
    # Informations
    collection = metadata.get('collection', '')
    collection_en = metadata.get('collection_en', '')
    
    header += f"📚 *الكتاب* | *Book* : {collection}"
    if collection_en:
        header += f"\n   ({collection_en})"
    header += "\n"
    
    if metadata.get('number'):
        header += f"🔢 *الرقم* | *Number* : {metadata['number']}\n"
    
    if metadata.get('grade'):
        grade = metadata['grade']
        if metadata.get('grade_en'):
            grade += f" ({metadata['grade_en']})"
        header += f"⭐ *الدرجة* | *Grade* : {grade}\n"
    
    # Date
    header += f"📅 *التاريخ الهجري* | *Hijri* : {hijri_date}\n"
    header += f"📆 *التاريخ الميلادي* | *Gregorian* : {gregorian_date}\n\n"
    
    # Séparateur
    header += "━" * 30 + "\n\n"
    
    # Texte du hadith
    hadith_section = f"*📖 نص الحديث | Hadith Text :*\n{hadith_text}\n\n"
    
    # Section explication
    explanation_section = ""
    
    if groq_explanation:
        # Explication Groq
        explanation_section = f"*⚡ شرح GroqCloud | GroqCloud Explanation :*\n{groq_explanation}\n\n"
        explanation_section += "━" * 30 + "\n"
    
    elif original_explanation:
        # Explication originale de HadeethEnc
        explanation_section = f"*📝 الشرح الأصلي | Original Explanation :*\n{original_explanation}\n\n"
        explanation_section += "━" * 30 + "\n"
    
    else:
        # Pas d'explication disponible
        explanation_section = "*📝 شرح | Explanation :*\n"
        explanation_section += "⚠️ *Explication non disponible avec la source actuelle*\n\n"
        explanation_section += "💡 *Suggestions :*\n"
        explanation_section += "• Consultez les commentaires classiques (Fath Al-Bari, Sharh Al-Nawawi)\n"
        explanation_section += "• Visitez https://dorar.net pour plus de détails\n\n"
    
    # Hashtags
    hashtags = "#حديث #Hadith #السنة #Sunnah #الإسلام #Islam"
    
    if groq_explanation:
        hashtags += " #GroqCloud #Llama3"
    
    if "البخاري" in collection:
        hashtags += " #البخاري #Bukhari"
    elif "مسلم" in collection:
        hashtags += " #مسلم #Muslim"
    
    # Assembler
    full_message = header + hadith_section + explanation_section + "\n" + hashtags
    
    return full_message


def send_telegram_message(message):
    """Envoie le message Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Gérer les longs messages (limite 4096 caractères)
    if len(message) > 4000:
        parts = []
        current_part = ""
        
        for line in message.split('\n'):
            if len(current_part) + len(line) + 1 < 4000:
                current_part += line + '\n'
            else:
                if current_part:
                    parts.append(current_part)
                current_part = line + '\n'
        
        if current_part:
            parts.append(current_part)
        
        success = True
        for i, part in enumerate(parts):
            part_num = i + 1
            part_text = f"*الجزء {part_num}/{len(parts)}* | *Part {part_num}/{len(parts)}*\n\n" + part
            
            if not send_single_message(part_text):
                success = False
            time.sleep(1)
        
        return success
    else:
        return send_single_message(message)


def send_single_message(text):
    """Envoie un seul message"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(
            url,
            data={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': text,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            },
            timeout=15
        )
        response.raise_for_status()
        return True
        
    except Exception as e:
        logging.error(f"❌ Erreur envoi: {e}")
        
        # Tentative sans Markdown
        try:
            clean_text = text.replace('*', '').replace('_', '').replace('`', '')
            response = requests.post(
                url,
                data={
                    'chat_id': TELEGRAM_CHAT_ID,
                    'text': clean_text,
                    'disable_web_page_preview': True
                },
                timeout=15
            )
            response.raise_for_status()
            logging.info("✅ Message envoyé (sans formatage)")
            return True
        except:
            return False


def test_hadeethenc_api():
    """Teste la connexion à HadeethEnc"""
    try:
        response = requests.get(
            f"{HadeethEncAPI.BASE_URL}/hadiths/random",
            params={"language": "ar"},
            timeout=10
        )
        return response.status_code == 200
    except:
        return False


def test_groq_connection():
    """Teste la connexion à GroqCloud"""
    if not groq_client:
        return False
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Test connection"}],
            max_tokens=10
        )
        return True
    except:
        return False


def run():
    """Fonction principale avec GroqCloud"""
    logging.info("=" * 50)
    logging.info("🚀 Démarrage du Bot Hadith avec GroqCloud")
    logging.info("=" * 50)
    
    # Vérifier Telegram
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.error("❌ Clés Telegram manquantes")
        return
    
    logging.info("✅ Configuration Telegram validée")
    
    # Vérifier Groq
    groq_ok = test_groq_connection()
    if groq_ok:
        logging.info("✅ GroqCloud disponible et fonctionnel")
    else:
        logging.warning("⚠️ GroqCloud non disponible - vérifiez votre clé API")
    
    # Tester HadeethEnc
    api_available = test_hadeethenc_api()
    
    if api_available:
        logging.info("✅ HadeethEnc.com disponible")
    else:
        logging.warning("⚠️ HadeethEnc.com indisponible, fallback HadithAPI")
    
    # Date
    hijri_date, gregorian_date = get_hijri_date()
    logging.info(f"📅 Date: {hijri_date} H / {gregorian_date}")
    
    # Récupérer le hadith
    hadith_data = None
    client_hadeeth = HadeethEncAPI()
    
    if api_available:
        logging.info("📖 Tentative HadeethEnc...")
        hadith_data = client_hadeeth.get_random_hadith(language="ar")
    
    if not hadith_data or not hadith_data.get('success'):
        logging.warning("⚠️ Utilisation fallback HadithAPI...")
        hadith_data = fallback_get_hadith()
    
    if hadith_data and hadith_data.get('success'):
        metadata = hadith_data['metadata']
        has_original = metadata.get('has_original_explanation', False)
        
        logging.info(f"✅ Hadith récupéré")
        logging.info(f"📚 Source: {metadata['source']}")
        logging.info(f"📚 Livre: {metadata.get('collection', 'Inconnu')}")
        logging.info(f"📝 Explication originale: {'✅' if has_original else '❌'}")
        
        # Générer l'explication avec Groq si disponible
        groq_explanation = None
        if groq_client:
            logging.info("🤖 Génération de l'explication avec GroqCloud...")
            explainer = GroqHadithExplainer(groq_client, model="llama")
            groq_explanation = explainer.generate_explanation(
                hadith_text=hadith_data['hadith_text'],
                metadata=metadata,
                language="fr"
            )
            
            if groq_explanation:
                logging.info(f"✅ Explication Groq générée avec succès")
            else:
                logging.warning("⚠️ Échec génération Groq")
        
        # Message
        message = format_telegram_message(
            hadith_data, 
            hijri_date, 
            gregorian_date,
            groq_explanation
        )
        
        # Envoyer
        logging.info("📤 Envoi Telegram...")
        if send_telegram_message(message):
            logging.info("✅ Succès!")
        else:
            logging.error("❌ Échec envoi")
    else:
        logging.error("❌ Aucun hadith disponible")
        error_message = """
🌙 *الخدمة غير متوفرة مؤقتاً*
🌙 *Service temporairement indisponible*

نأسف، لم نتمكن من استرجاع حديث اليوم.
الرجاء المحاولة لاحقاً.

Désolé, impossible de récupérer le hadith aujourd'hui.
Veuillez réessayer plus tard.

#حديث #Hadith
        """
        send_telegram_message(error_message)
    
    logging.info("=" * 50)


if __name__ == "__main__":
    run()
