#!/usr/bin/env python3
"""
translation_service.py

Handles translation and query enhancement for multilingual support.
Provides fallback strategies for low-confidence queries.
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

# Optional: Google Translate for production
try:
    from googletrans import Translator
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False

# Import indic-trans2 for Indian languages (optional)
try:
    from indicnlp.transliterate import unicode_transliterate
    INDIC_TRANS_AVAILABLE = True
except ImportError:
    INDIC_TRANS_AVAILABLE = False


class TranslationService:
    """
    Service for handling multilingual queries and translations.
    Supports EN, HI, BN, MR and other Indian languages.
    """
    
    def __init__(self, use_online=False):
        """
        Initialize translation service.
        
        Args:
            use_online: Whether to use online translation services (requires API keys)
        """
        self.use_online = use_online and GOOGLE_TRANSLATE_AVAILABLE
        
        if self.use_online:
            self.translator = Translator()
        
        # Load offline translation mappings
        self.load_offline_mappings()
        
        # Common occupation terms in multiple languages
        self.multilingual_terms = self.load_multilingual_terms()
    
    def load_offline_mappings(self):
        """Load offline translation mappings for common occupation terms."""
        # Hindi occupation term mappings
        self.hindi_mappings = {
            # Common job titles
            'शिक्षक': 'teacher',
            'अध्यापक': 'teacher',
            'डॉक्टर': 'doctor',
            'चिकित्सक': 'doctor',
            'इंजीनियर': 'engineer',
            'अभियंता': 'engineer',
            'नर्स': 'nurse',
            'ड्राइवर': 'driver',
            'चालक': 'driver',
            'किसान': 'farmer',
            'कृषक': 'farmer',
            'मजदूर': 'laborer',
            'श्रमिक': 'worker',
            'कारीगर': 'craftsman',
            'व्यापारी': 'trader',
            'दुकानदार': 'shopkeeper',
            'लिपिक': 'clerk',
            'प्रबंधक': 'manager',
            'सुरक्षा गार्ड': 'security guard',
            'रसोइया': 'cook',
            'बावर्ची': 'cook',
            'दर्जी': 'tailor',
            'बढ़ई': 'carpenter',
            'मिस्त्री': 'mechanic',
            'इलेक्ट्रीशियन': 'electrician',
            'प्लंबर': 'plumber',
            'पेंटर': 'painter',
            'वेल्डर': 'welder',
            
            # Sectors
            'कृषि': 'agriculture',
            'उद्योग': 'industry',
            'सेवा': 'service',
            'निर्माण': 'construction',
            'परिवहन': 'transport',
            'शिक्षा': 'education',
            'स्वास्थ्य': 'health',
            'वित्त': 'finance',
            'प्रौद्योगिकी': 'technology',
        }
        
        # Bengali mappings
        self.bengali_mappings = {
            'শিক্ষক': 'teacher',
            'ডাক্তার': 'doctor',
            'ইঞ্জিনিয়ার': 'engineer',
            'নার্স': 'nurse',
            'ড্রাইভার': 'driver',
            'কৃষক': 'farmer',
            'শ্রমিক': 'worker',
            'কারিগর': 'craftsman',
            'ব্যবসায়ী': 'trader',
            'দোকানদার': 'shopkeeper',
            'কেরানি': 'clerk',
            'ম্যানেজার': 'manager',
            'রাঁধুনি': 'cook',
            'দর্জি': 'tailor',
            'কাঠমিস্ত্রি': 'carpenter',
            'মিস্ত্রি': 'mechanic',
        }
        
        # Marathi mappings
        self.marathi_mappings = {
            'शिक्षक': 'teacher',
            'डॉक्टर': 'doctor',
            'अभियंता': 'engineer',
            'नर्स': 'nurse',
            'ड्रायव्हर': 'driver',
            'शेतकरी': 'farmer',
            'कामगार': 'worker',
            'कारागीर': 'craftsman',
            'व्यापारी': 'trader',
            'दुकानदार': 'shopkeeper',
            'लिपिक': 'clerk',
            'व्यवस्थापक': 'manager',
            'स्वयंपाकी': 'cook',
            'शिंपी': 'tailor',
            'सुतार': 'carpenter',
        }
        
        self.offline_mappings = {
            'hi': self.hindi_mappings,
            'bn': self.bengali_mappings,
            'mr': self.marathi_mappings
        }
    
    def load_multilingual_terms(self) -> Dict[str, List[str]]:
        """Load multilingual occupation terms for fuzzy matching."""
        return {
            'teacher': ['teacher', 'instructor', 'educator', 'tutor', 'professor', 'lecturer'],
            'doctor': ['doctor', 'physician', 'medical officer', 'surgeon', 'specialist'],
            'engineer': ['engineer', 'technical officer', 'technologist'],
            'driver': ['driver', 'chauffeur', 'operator', 'pilot'],
            'farmer': ['farmer', 'agriculturist', 'cultivator', 'grower'],
            'worker': ['worker', 'laborer', 'employee', 'staff'],
            'mechanic': ['mechanic', 'technician', 'repairman', 'fitter'],
            'cook': ['cook', 'chef', 'kitchen staff', 'culinary worker'],
        }
    
    def translate_query(self, query: str, source_lang: str, target_lang: str = 'en') -> str:
        """
        Translate query from source language to target language.
        
        Args:
            query: Input query text
            source_lang: Source language code (hi, bn, mr, etc.)
            target_lang: Target language code (default: en)
        
        Returns:
            Translated query or original if translation fails
        """
        if source_lang == target_lang:
            return query
        
        # Try offline translation first
        translated = self.offline_translate(query, source_lang, target_lang)
        if translated != query:
            return translated
        
        # Try online translation if available
        if self.use_online:
            try:
                result = self.translator.translate(query, src=source_lang, dest=target_lang)
                return result.text
            except Exception as e:
                logging.warning(f"Online translation failed: {e}")
        
        return query
    
    def offline_translate(self, query: str, source_lang: str, target_lang: str) -> str:
        """
        Offline translation using predefined mappings.
        """
        if source_lang not in self.offline_mappings:
            return query
        
        mappings = self.offline_mappings[source_lang]
        query_lower = query.lower()
        
        # Direct mapping
        if query_lower in mappings:
            return mappings[query_lower]
        
        # Partial matching
        translated_parts = []
        for word in query.split():
            word_lower = word.lower()
            if word_lower in mappings:
                translated_parts.append(mappings[word_lower])
            else:
                # Keep original word if no translation found
                translated_parts.append(word)
        
        return ' '.join(translated_parts)
    
    def generate_query_variations(self, query: str, language: str = 'en') -> List[str]:
        """
        Generate query variations for better matching.
        Includes synonyms, alternate spellings, and related terms.
        """
        variations = [query]
        query_lower = query.lower()
        
        # Add synonyms
        for base_term, synonyms in self.multilingual_terms.items():
            if base_term in query_lower:
                for synonym in synonyms:
                    variation = query_lower.replace(base_term, synonym)
                    if variation != query_lower:
                        variations.append(variation)
        
        # Add common variations
        # Remove common suffixes
        suffixes_to_remove = ['er', 'or', 'ist', 'ian', 'man']
        for suffix in suffixes_to_remove:
            if query_lower.endswith(suffix):
                base = query_lower[:-len(suffix)]
                variations.append(base)
        
        # Add common prefixes
        prefixes = ['senior', 'junior', 'assistant', 'chief', 'head']
        base_query = query_lower
        for prefix in prefixes:
            if not base_query.startswith(prefix):
                variations.append(f"{prefix} {base_query}")
        
        # Remove duplicates and return
        return list(set(variations))[:5]  # Limit to 5 variations
    
    def enhance_low_confidence_query(self, query: str, language: str) -> Dict[str, any]:
        """
        Enhance a low-confidence query with suggestions and alternatives.
        
        Returns:
            Dictionary with enhanced query information
        """
        enhanced = {
            'original_query': query,
            'language': language,
            'suggestions': [],
            'alternatives': [],
            'translated': None,
            'spell_corrected': None
        }
        
        # Generate variations
        enhanced['alternatives'] = self.generate_query_variations(query, language)
        
        # Translate if not English
        if language != 'en':
            enhanced['translated'] = self.translate_query(query, language, 'en')
            if enhanced['translated'] != query:
                # Generate variations for translated query too
                enhanced['alternatives'].extend(
                    self.generate_query_variations(enhanced['translated'], 'en')
                )
        
        # Spell correction suggestions (simple approach)
        enhanced['spell_corrected'] = self.simple_spell_correct(query)
        
        # Generate helpful suggestions
        enhanced['suggestions'] = self.generate_suggestions(query, language)
        
        return enhanced
    
    def simple_spell_correct(self, query: str) -> Optional[str]:
        """
        Simple spell correction for common mistakes.
        In production, use a proper spell checker.
        """
        common_corrections = {
            'enginer': 'engineer',
            'docter': 'doctor',
            'teachar': 'teacher',
            'maneger': 'manager',
            'electrisian': 'electrician',
            'plumbar': 'plumber',
            'lawer': 'lawyer',
            'accountent': 'accountant',
            'secretery': 'secretary',
        }
        
        query_lower = query.lower()
        for wrong, correct in common_corrections.items():
            if wrong in query_lower:
                return query_lower.replace(wrong, correct)
        
        return None
    
    def generate_suggestions(self, query: str, language: str) -> List[str]:
        """
        Generate helpful suggestions for users when query has low confidence.
        """
        suggestions = []
        
        # Language-specific suggestions
        if language == 'hi':
            suggestions.append("कृपया अंग्रेजी में भी खोजने का प्रयास करें")
            suggestions.append("व्यवसाय का पूरा नाम लिखें")
        elif language == 'bn':
            suggestions.append("অনুগ্রহ করে ইংরেজিতেও অনুসন্ধান করুন")
            suggestions.append("পেশার সম্পূর্ণ নাম লিখুন")
        elif language == 'mr':
            suggestions.append("कृपया इंग्रजीत देखील शोधण्याचा प्रयत्न करा")
            suggestions.append("व्यवसायाचे पूर्ण नाव लिहा")
        else:
            suggestions.append("Try using more specific job titles")
            suggestions.append("Include the industry or sector (e.g., 'software engineer', 'civil engineer')")
            suggestions.append("Avoid abbreviations and use full terms")
        
        # Add example based on query length
        if len(query.split()) == 1:
            suggestions.append("Try adding qualifiers (e.g., 'senior', 'assistant', sector name)")
        
        return suggestions[:3]  # Return top 3 suggestions


class MultilingualSynonymBank:
    """
    Manages multilingual synonyms for occupations.
    """
    
    def __init__(self, synonym_file: Optional[Path] = None):
        """Initialize synonym bank."""
        self.synonym_file = synonym_file or Path("backend/data/synonyms.json")
        self.synonyms = self.load_synonyms()
    
    def load_synonyms(self) -> Dict[str, Dict[str, List[str]]]:
        """Load synonyms from file."""
        if self.synonym_file.exists():
            with open(self.synonym_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_synonyms(self):
        """Save synonyms to file."""
        self.synonym_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.synonym_file, 'w', encoding='utf-8') as f:
            json.dump(self.synonyms, f, ensure_ascii=False, indent=2)
    
    def add_synonym(self, nco_code: str, synonym: str, language: str = 'en'):
        """Add a synonym for an occupation."""
        if nco_code not in self.synonyms:
            self.synonyms[nco_code] = {}
        
        if language not in self.synonyms[nco_code]:
            self.synonyms[nco_code][language] = []
        
        if synonym not in self.synonyms[nco_code][language]:
            self.synonyms[nco_code][language].append(synonym)
            self.save_synonyms()
    
    def remove_synonym(self, nco_code: str, synonym: str, language: str = 'en'):
        """Remove a synonym for an occupation."""
        if nco_code in self.synonyms and language in self.synonyms[nco_code]:
            if synonym in self.synonyms[nco_code][language]:
                self.synonyms[nco_code][language].remove(synonym)
                self.save_synonyms()
    
    def get_synonyms(self, nco_code: str, language: str = None) -> List[str]:
        """Get synonyms for an occupation."""
        if nco_code not in self.synonyms:
            return []
        
        if language:
            return self.synonyms[nco_code].get(language, [])
        
        # Return all synonyms across languages
        all_synonyms = []
        for lang_synonyms in self.synonyms[nco_code].values():
            all_synonyms.extend(lang_synonyms)
        return all_synonyms


if __name__ == "__main__":
    # Test the translation service
    service = TranslationService(use_online=False)
    
    # Test Hindi translation
    print("Testing Hindi translations:")
    test_queries_hi = ["शिक्षक", "डॉक्टर", "इंजीनियर", "किसान"]
    for query in test_queries_hi:
        translated = service.translate_query(query, 'hi', 'en')
        print(f"  {query} -> {translated}")
    
    # Test query enhancement
    print("\nTesting query enhancement:")
    enhanced = service.enhance_low_confidence_query("enginer", "en")
    print(f"  Original: {enhanced['original_query']}")
    print(f"  Corrected: {enhanced['spell_corrected']}")
    print(f"  Alternatives: {enhanced['alternatives']}")
    print(f"  Suggestions: {enhanced['suggestions']}")
