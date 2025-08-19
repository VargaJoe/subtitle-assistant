#!/usr/bin/env python3
"""
Test enhanced parenthetical translation with preprocessing.
"""

from subtitle_translator.marian_client import MarianClient
from subtitle_translator.config import Config

def preprocess_for_translation(text: str) -> str:
    """Preprocess text to make it more translatable."""
    # Dictionary of technical terms to more translatable equivalents
    replacements = {
        'INDISTINCT': 'unclear',
        'RADIO CHATTER': 'radio conversation',
        'DOOR SLAMS': 'door closing loudly',
        'PHONE RINGING': 'phone is ringing',
        'ENGINE STARTS': 'engine starting',
        'ALARM SOUNDS': 'alarm is sounding',
    }
    
    processed = text
    for technical_term, simple_term in replacements.items():
        processed = processed.replace(technical_term, simple_term)
    
    return processed

def postprocess_translation(original: str, translated: str) -> str:
    """Post-process translation to restore appropriate formatting."""
    # If translation didn't change and it's all caps, try to keep it as sound effect
    if original == translated and original.isupper():
        return original  # Keep original for untranslatable technical terms
    return translated

def test_enhanced_translation():
    """Test enhanced parenthetical translation."""
    
    config = Config()
    config.source_lang = "en"
    config.target_lang = "hu"
    config.translation_backend = "marian"
    
    marian_client = MarianClient(config)
    
    test_cases = [
        "(INDISTINCT RADIO CHATTER)",
        "(DOOR SLAMS)",
        "(PHONE RINGING)",
        "(ENGINE STARTS)",
    ]
    
    print("Enhanced Parenthetical Translation Test")
    print("=" * 50)
    
    for original in test_cases:
        # Test original
        direct_translation = marian_client._translate_single_line(original)
        
        # Test with preprocessing
        preprocessed = preprocess_for_translation(original)
        enhanced_translation = marian_client._translate_single_line(preprocessed)
        final_result = postprocess_translation(original, enhanced_translation)
        
        print(f"Original:     {repr(original)}")
        print(f"Direct:       {repr(direct_translation)}")
        print(f"Preprocessed: {repr(preprocessed)}")
        print(f"Enhanced:     {repr(enhanced_translation)}")
        print(f"Final:        {repr(final_result)}")
        print()

if __name__ == "__main__":
    test_enhanced_translation()
