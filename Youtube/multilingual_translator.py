import requests
import json
from typing import Optional, List, Dict
import time
from enum import Enum

class Language(Enum):
    ENGLISH = "English"
    FRENCH = "French"
    GERMAN = "German"
    HINDI = "Hindi"
    ITALIAN = "Italian"
    PORTUGUESE = "Portuguese"
    SPANISH = "Spanish"
    THAI = "Thai"

class MultilingualTranslator:
    def __init__(self, api_url: str = "http://x.x.x.x:11434"):
        """
        Initialize the multilingual translator
        
        Args:
            api_url (str): Ollama API endpoint
        """
        self.api_url = api_url.rstrip('/')
        self.model = "llama3.3:latest"
        self.headers = {
            "Content-Type": "application/json"
        }
        
        # Language codes and prompts
        self.language_prompts = {
            Language.FRENCH: "français",
            Language.GERMAN: "Deutsch",
            Language.HINDI: "हिंदी",
            Language.ITALIAN: "italiano",
            Language.PORTUGUESE: "português",
            Language.SPANISH: "español",
            Language.THAI: "ไทย",
            Language.ENGLISH: "English"
        }

    def translate(self, 
                 text: str, 
                 source_lang: Language, 
                 target_lang: Language, 
                 retries: int = 2) -> str:
        """
        Translate text between supported languages
        
        Args:
            text (str): Text to translate
            source_lang (Language): Source language
            target_lang (Language): Target language
            retries (int): Number of retries for failed attempts
            
        Returns:
            str: Translated text
        """
        if source_lang == target_lang:
            return text

        # Create a clear translation prompt
        system_prompt = f"""
        You are a professional translator. Translate the following {source_lang.value} text to {target_lang.value}.
        Rules:
        1. Maintain the original meaning and tone
        2. Use proper grammar and vocabulary for {target_lang.value}
        3. Keep proper nouns as needed
        4. Return only the translation, without explanations
        5. Ensure high-quality translation specific to {target_lang.value}
        
        Text to translate:
        """
        
        attempt = 0
        while attempt <= retries:
            try:
                response = requests.post(
                    f"{self.api_url}/api/generate",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "prompt": f"{system_prompt}\n{text}\n\n{target_lang.value} translation:",
                        "temperature": 0.3,
                        "max_tokens": 2000,
                        "top_p": 0.95,
                        "stream": False
                    },
                    timeout=60
                )
                
                response.raise_for_status()
                translation_data = response.json()
                
                if "response" in translation_data:
                    return translation_data["response"].strip()
                else:
                    return f"Translation error to {target_lang.value}"
                    
            except requests.exceptions.Timeout:
                if attempt < retries:
                    time.sleep(2)
                    attempt += 1
                    continue
                return "Server timeout - please try again."
                
            except requests.exceptions.RequestException as e:
                if attempt < retries:
                    time.sleep(2)
                    attempt += 1
                    continue
                return f"API error: {str(e)}"
                
            except json.JSONDecodeError:
                return "Data processing error"
            
            attempt += 1

def main():
    """Main function to demonstrate multilingual translation"""
    translator = MultilingualTranslator()
    
    # Example texts in different languages
    example_translations = [
        (Language.ENGLISH, "Hello, how are you? I hope you're having a great day!"),
        (Language.FRENCH, "Bonjour, comment allez-vous? J'espère que vous passez une excellente journée!"),
        (Language.HINDI, "नमस्ते, आप कैसे हैं? मुझे आशा है कि आपका दिन अच्छा जा रहा है!"),
        (Language.SPANISH, "¡Hola, ¿cómo estás? ¡Espero que estés teniendo un gran día!")
    ]
    
    print("\nMultilingual Translator (Using Llama 3.3)\n")
    print("Supported languages:", ", ".join([lang.value for lang in Language]))
    print("-" * 50)
    
    # Demonstrate translations
    for source_lang, text in example_translations:
        print(f"\nOriginal ({source_lang.value}):", text)
        
        # Translate to all other languages
        for target_lang in Language:
            if target_lang != source_lang:
                translation = translator.translate(text, source_lang, target_lang)
                print(f"\n{target_lang.value}:", translation)
        
        print("-" * 50)
        time.sleep(1)

    # Interactive mode
    print("\nInteractive Translation Mode")
    print("Type 'quit' to exit\n")
    
    while True:
        # Get source language
        print("\nAvailable languages:")
        for i, lang in enumerate(Language, 1):
            print(f"{i}. {lang.value}")
            
        try:
            source_idx = int(input("\nSelect source language number (or 0 to quit): ")) - 1
            if source_idx == -1:
                break
            source_lang = list(Language)[source_idx]
            
            target_idx = int(input("Select target language number: ")) - 1
            target_lang = list(Language)[target_idx]
            
            text = input(f"\nEnter {source_lang.value} text to translate: ")
            
            translation = translator.translate(text, source_lang, target_lang)
            print(f"\n{target_lang.value} translation:", translation)
            print("-" * 50)
            
        except (ValueError, IndexError):
            print("Invalid selection. Please try again.")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
