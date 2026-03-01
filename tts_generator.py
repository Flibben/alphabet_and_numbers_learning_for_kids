import os
import time
import questionary
from tqdm import tqdm
import io
from pydub import AudioSegment

from google.cloud import texttospeech
from google.api_core.client_options import ClientOptions

# --- Configuration & Data ---

APP_LANGUAGES = {
    "sv": {"flag": "🇸🇪", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ"), "numbers": list("0123456789")},
    "en": {"flag": "🇬🇧", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "numbers": list("0123456789")},
    "es": {"flag": "🇪🇸", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZÑ"), "numbers": list("0123456789")},
    "de": {"flag": "🇩🇪", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ"), "numbers": list("0123456789")},
    "fr": {"flag": "🇫🇷", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "numbers": list("0123456789")},
    "it": {"flag": "🇮🇹", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "numbers": list("0123456789")},
    "pt": {"flag": "🇵🇹", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "numbers": list("0123456789")},
    "nl": {"flag": "🇳🇱", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "numbers": list("0123456789")},
    "pl": {"flag": "🇵🇱", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZĄĆĘŁŃÓŚŹŻ"), "numbers": list("0123456789")},
    "da": {"flag": "🇩🇰", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅ"), "numbers": list("0123456789")},
    "no": {"flag": "🇳🇴", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZÆØÅ"), "numbers": list("0123456789")},
    "fi": {"flag": "🇫🇮", "letters": list("ABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ"), "numbers": list("0123456789")}
}

TRANSLATIONS = {
    "sv": {"letter": "Det här är bokstaven", "number": "Det här är siffran"},
    "en": {"letter": "This is the letter", "number": "This is the number"},
    "es": {"letter": "Esta es la letra", "number": "Este es el número"},
    "de": {"letter": "Das ist der Buchstabe", "number": "Das ist die Nummer"},
    "fr": {"letter": "C'est la lettre", "number": "C'est le numéro"},
    "it": {"letter": "Questa è la lettera", "number": "Questo è il numero"},
    "pt": {"letter": "Esta é a letra", "number": "Este é o número"},
    "nl": {"letter": "Dit is de letter", "number": "Dit is het nummer"},
    "pl": {"letter": "To jest litera", "number": "To jest numer"},
    "da": {"letter": "Dette er bogstavet", "number": "Dette er nummeret"},
    "no": {"letter": "Dette er bokstaven", "number": "Dette er tallet"},
    "fi": {"letter": "Tämä on kirjain", "number": "Tämä on numero"},
}

GOOGLE_LANG_CODES = {
    'sv': 'sv-SE', 'en': 'en-GB', 'es': 'es-ES', 'de': 'de-DE',
    'fr': 'fr-FR', 'it': 'it-IT', 'pt': 'pt-PT', 'nl': 'nl-NL',
    'pl': 'pl-PL', 'da': 'da-DK', 'no': 'nb-NO', 'fi': 'fi-FI'
}

GEMINI_VOICES = ["Kore", "Callirrhoe", "Aoede", "Charon", "Puck", "Enceladus"]

class TTSApp:
    def __init__(self):
        self.client = None
        self.selected_langs = []
        self.output_dir = "audio"
        self.tts_voice = "Kore"
        # Prompt explicitly instructs the AI to handle the pause after the first letter
        self.tts_prompt = "You are teaching a young child, 2 years old, the alphabet. Have a positive attitude in your voice, upbeat and encouraging. Always say the name of the letter, do not sound it out."

    def clear_screen(self):
        # ANSI codes: Clear screen (\033[2J) and move cursor to top-left (\033[H)
        # This fixes the "empty lines" issue in VS Code terminal
        print("\033[2J\033[H", end="", flush=True)

    def get_client(self):
        if not self.client:
            try:
                options = ClientOptions(api_endpoint="texttospeech.googleapis.com")
                self.client = texttospeech.TextToSpeechClient(client_options=options)
            except Exception as e:
                print(f"Error initializing client: {e}")
        return self.client

    def synthesize(self, text_to_speak, prompt_instructions, lang_code, voice_name):
        client = self.get_client()
        if not client: return None

        synthesis_input = texttospeech.SynthesisInput(text=text_to_speak, prompt=prompt_instructions)
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=lang_code, name=voice_name, model_name="gemini-2.5-pro-tts"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16, sample_rate_hertz=24000
        )

        try:
            # 90 second timeout prevents the 499 "Cancelled" errors
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice_params, audio_config=audio_config, timeout=90.0
            )
            
            # Process into high-quality 128kbps Mono MP3
            raw_audio = io.BytesIO(response.audio_content)
            audio_segment = AudioSegment.from_wav(raw_audio)
            normalized_audio = audio_segment.normalize()
            
            mp3_output = io.BytesIO()
            normalized_audio.set_channels(1).export(mp3_output, format="mp3", bitrate="128k")
            return mp3_output.getvalue()
        except Exception as e:
            return None

    def menu_select_languages(self):
        choices = [
            questionary.Choice(title=f"{data['flag']} {lang.upper()}", value=lang, checked=(lang in self.selected_langs))
            for lang, data in APP_LANGUAGES.items()
        ]
        selected = questionary.checkbox("Select Languages (Arrows + Space):", choices=choices).ask()
        if selected is not None: self.selected_langs = selected

    def menu_select_voice(self):
        choices = [questionary.Choice(f"{i+1}. {v}", value=v, shortcut_key=str(i+1)) for i, v in enumerate(GEMINI_VOICES)]
        choice = questionary.select(f"Select Voice (Current: {self.tts_voice}):", choices=choices, use_shortcuts=True).ask()
        if choice: self.tts_voice = choice

    def menu_set_prompt(self):
        new_prompt = questionary.text("Enter TTS Prompt:", default=self.tts_prompt).ask()
        if new_prompt: self.tts_prompt = new_prompt.strip()

    def menu_demo_mode(self):
        self.clear_screen()
        if not self.selected_langs:
            input("Please select a language first. Press Enter..."); return

        lang = self.selected_langs[0]
        char = questionary.text(f"Enter a character (e.g., 'A' or '1') [{lang}]:").ask()
        if not char: return

        item_type = 'number' if char.isdigit() else 'letter'
        trans = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
        # The fix: "A... This is the letter A."
        full_text = f"{char}... {trans[item_type]} {char}."

        print(f"\nSynthesizing: {full_text}...")
        audio = self.synthesize(full_text, self.tts_prompt, GOOGLE_LANG_CODES[lang], self.tts_voice)
        
        if audio:
            path = os.path.join(self.output_dir, f"demo_{char}.mp3")
            os.makedirs(self.output_dir, exist_ok=True)
            with open(path, "wb") as f: f.write(audio)
            print(f"Success! Saved to {path}")
        else:
            print("Failed.")
        input("\nPress Enter...")

    def run_batch(self):
        self.clear_screen()
        if not self.selected_langs:
            input("No languages selected. Press Enter..."); return

        confirm = questionary.confirm("Start batch? (Existing files in 'audio/' will be overwritten)").ask()
        if not confirm: return
        
        total_ops = sum(len(APP_LANGUAGES[lang]['letters']) + len(APP_LANGUAGES[lang]['numbers']) for lang in self.selected_langs)

        with tqdm(total=total_ops, desc="Generating Audio", unit="file") as pbar:
            for lang in self.selected_langs:
                lang_config = APP_LANGUAGES[lang]
                trans = TRANSLATIONS.get(lang, TRANSLATIONS['en'])
                google_lang = GOOGLE_LANG_CODES.get(lang, 'en-US')
                lang_folder = os.path.join(self.output_dir, lang)
                os.makedirs(lang_folder, exist_ok=True)

                items = [('letter', c) for c in lang_config['letters']] + [('number', n) for n in lang_config['numbers']]

                for item_type, char in items:
                    # FIX: Always announce the character first for the app
                    text_script = f"{char}... {trans[item_type]} {char}."
                    
                    audio = None
                    for _ in range(3): # Retry loop
                        audio = self.synthesize(text_script, self.tts_prompt, google_lang, self.tts_voice)
                        if audio: break
                        time.sleep(1)

                    if audio:
                        with open(os.path.join(lang_folder, f"{char}.mp3"), "wb") as f: f.write(audio)
                    else:
                        # pbar.write prevents duplication of the progress bar lines
                        pbar.write(f"FAILED: {lang} - {char}")
                    
                    pbar.update(1)
        input("\nBatch complete! Press Enter...")

    def main_menu(self):
        while True:
            self.clear_screen()
            print("==========================================")
            print("   Google Cloud TTS Generator (Gemini)    ")
            print("==========================================")
            print(f"Selected: {self.selected_langs}")
            print(f"Voice: {self.tts_voice} | Prompt: '{self.tts_prompt[:30]}...'")
            print("------------------------------------------\n")
            
            choice = questionary.select(
                "Select option (Numbers 1-6):",
                choices=[
                    questionary.Choice("1. Select Languages", value="1", shortcut_key="1"),
                    questionary.Choice("2. Select Voice", value="2", shortcut_key="2"),
                    questionary.Choice("3. Set Prompt Settings", value="3", shortcut_key="3"),
                    questionary.Choice("4. Demo Mode", value="4", shortcut_key="4"),
                    questionary.Choice("5. Run Batch", value="5", shortcut_key="5"),
                    questionary.Choice("6. Exit", value="6", shortcut_key="6")
                ],
                use_shortcuts=True
            ).ask()
            
            if choice == '1': self.menu_select_languages()
            elif choice == '2': self.menu_select_voice()
            elif choice == '3': self.menu_set_prompt()
            elif choice == '4': self.menu_demo_mode()
            elif choice == '5': self.run_batch()
            elif choice == '6' or choice is None: break

if __name__ == "__main__":
    app = TTSApp()
    app.main_menu()